# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import io
import json
import logging
import logging.config
import os
import re
import sys
import warnings
from threading import Event

import click
import jinja2
import yaml

import jsonschema
from jsonschema import validate
from jsonschema import Draft7Validator

from jsonschema.validators import extend

warnings.filterwarnings("ignore", category=DeprecationWarning)

import imp
from functools import reduce

from .utils import (
    Map,
    PythonExpression,
    deep_find,
    deep_merge,
    import_class,
    merge_dicts,
    randomString,
    str2bool,
)

# they must be in a form ${VARIABLE_NAME}
ENVNAME_PATTERN = "[A-Z0-9_]+"
ENVPARAM_PATTERN = "\$\{%s\}" % ENVNAME_PATTERN

# consolidated variables supplied via env file and environment variables
ENV = {}

DEBUG = str2bool(os.getenv("JA2MQTT_DEBUG", "False"))
ANSI_COLORS = not str2bool(os.getenv("JA2MQTT_NO_ANSI", "False"))
CONFIG_FILE = os.getenv("JA2MQTT_CONFIG", None)
CONFIG_ENV = os.getenv("JA2MQTT_ENV", None)

env_variables = ["JA2MQTT_DEBUG", "JA2MQTT_NO_ANSI", "JA2MQTT_CONFIG", "JA2MQTT_ENV"]

ENCODING = "ascii"

# global exit event
exit_event = Event()

# valid schema versions
SCHEMA_VERSIONS = ["1.0"]


class Jinja2TemplateLoader(jinja2.BaseLoader):
    def get_source(self, environment, template):
        if not os.path.exists(template):
            raise jinja2.TemplateNotFound(template)
        with open(template, "r", encoding="utf-8") as f:
            source = f.read()
        return source, template, lambda: True


class Jinja2Template(io.BytesIO):
    name = None

    def size(self):
        self.seek(0, io.SEEK_END)
        size = self.tell()
        self.seek(0, io.SEEK_SET)
        return size

    def __init__(self, file, scope=None, strip_blank_lines=False):
        super(Jinja2Template, self).__init__(None)
        self.name = file
        env = jinja2.Environment(
            loader=Jinja2TemplateLoader(), trim_blocks=True, lstrip_blocks=True
        )
        if scope is not None:
            env.globals.update(scope)
        try:
            content = env.get_template(file).render()
            if strip_blank_lines:
                content = "\n".join([x for x in content.split("\n") if x.strip() != ""])
            self.write(content.encode())
            self.seek(0)
        except Exception as e:
            raise Exception(
                f"Error when processing template {os.path.basename(file)}: {str(e)}"
            )


def get_schema_file(name):
    sfile = os.path.dirname(os.path.realpath(__file__)) + f"/schemas/{name}"
    if not os.path.exists(sfile):
        raise Exception(f"The schema {sfile} does not exist!")
    return sfile


def get_dir_path(config_dir, path, base_dir=None, check=False):
    """
    Return the directory for the path specified.
    """
    d = os.path.normpath(
        (
            ((config_dir if base_dir is None else base_dir) + "/")
            if path[0] != "/"
            else ""
        )
        + path
    )
    if check and not os.path.exists(d):
        raise Exception(f"The directory {d} does not exist!")
    return d


def init_env(env_file, sep="=", comment="#"):
    """
    Read environment varialbes from the `env_file` and combines them with the OS environment variables.
    """
    env = {}
    for k, v in os.environ.items():
        env[k] = v
    if env_file:
        with open(env_file, "rt") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith(comment):
                    key_value = l.split(sep)
                    key = key_value[0].strip()
                    if not re.match(f"^{ENVNAME_PATTERN}$", key):
                        raise Exception(f"Invalid variable name '{key}'.")
                    value = sep.join(key_value[1:]).strip().strip("\"'")
                    env[key] = value
    return env


def read_config(config_file, env_file, use_template, scope=None):
    if not (os.path.exists(config_file)):
        raise Exception(f"The configuration file {config_file} does not exist!")
    if env_file and not (os.path.exists(env_file)):
        raise Exception(f"The environment file {env_file} does not exist!")

    # init yaml reader
    global ENV
    ENV = init_env(env_file)
    yaml.add_implicit_resolver("!env", re.compile(r".*%s.*" % ENVPARAM_PATTERN))
    yaml.add_constructor("!env", env_constructor)
    yaml.add_constructor("!py", py_constructor)

    config_file = os.path.realpath(config_file)
    stream = (
        open(config_file, "r", encoding="utf-8")
        if not use_template
        else Jinja2Template(config_file, scope, strip_blank_lines=True)
    )
    try:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    except Exception as e:
        raise Exception(
            f"Error when reading the configuration file {config_file}: {str(e)}"
        )
    finally:
        stream.close()
    config_dir = os.path.dirname(config_file)
    return config, config_file, config_dir


def replace_env_variable(value):
    """
    Replace all environment varaibles in a string privided in `value` parameter
    with values of variable in `ENV` global variable.
    """
    params = list(set(re.findall("(%s)" % ENVPARAM_PATTERN, value)))
    if len(params) > 0:
        for k in params:
            env_value = ENV.get(k[2:-1])
            if env_value is None:
                raise Exception(f"The environment variable {k} does not exist!")
            else:
                value = value.replace(k, env_value)
    return value


def env_constructor(loader, node):
    """
    A constructor for environment varaibles provided in the yaml configuration file.
    It populates strings that contain environment variables in a form `${var_name}` with
    their values.
    """
    return replace_env_variable(node.value)


def py_constructor(loader, node):
    """
    A constructor for Python expression in the yaml configuration file. The python expression
    must be prefixed by `!py` directive. The result is the `PythonExpression` object.
    """
    try:
        return PythonExpression(replace_env_variable(node.value))
    except Exception as e:
        raise Exception(
            'Cannot create python expression from string "%s". %s'
            % (node.value, str(e))
        )


class Config:
    """
    The main confuguration.
    """

    def __init__(
        self,
        file,
        env=None,
        schema=None,
        log_level="INFO",
        scope=None,
        use_template=False,
    ):
        """
        Read and parse the configuration from the yaml file and initializes the logging.
        """
        self.schema = None
        self.log_level = log_level
        if not (os.path.exists(file)):
            raise Exception(f"The configuration file {file} does not exist!")
        self.raw_config, self.config_file, self.config_dir = read_config(
            file, env, use_template=use_template, scope=scope
        )
        self.root = self.get_part(None)
        if schema:
            self.schema = read_config(
                get_schema_file(schema), None, use_template=False
            )[0]

    def check_dupplicates(self, path):
        _path = path.split(".")
        _prop = _path[-1]
        values = [x[_prop] for x in self(".".join(_path[:-1]), [], required=False)]
        dupplicates = list(set([x for x in values if values.count(x) > 1]))
        if len(dupplicates) > 0:
            raise Exception(f"There are dupplicate values in '{path}': {dupplicates}")

    def validate(self, throw_ex=True):
        def __version(c, i):
            return i in SCHEMA_VERSIONS

        def __python_expr_or_int(c, i):
            return isinstance(i, PythonExpression) or isinstance(i, int)

        def __python_expr_or_str(c, i):
            return isinstance(i, PythonExpression) or isinstance(i, str)

        def __python_expr_or_str_or_number(c, i):
            return (
                isinstance(i, PythonExpression)
                or isinstance(i, str)
                or isinstance(i, int)
                or isinstance(i, float)
            )

        type_checker = Draft7Validator.TYPE_CHECKER.redefine_many(
            Map(
                __version=__version,
                __python_expr_or_int=__python_expr_or_int,
                __python_expr_or_str=__python_expr_or_str,
                __python_expr_or_str_or_number=__python_expr_or_str_or_number,
            )
        )
        ConfigValidator = extend(Draft7Validator, type_checker=type_checker)
        validator = ConfigValidator(self.schema)
        errors = list(validator.iter_errors(self.raw_config))

        if errors:
            if throw_ex:
                raise Exception(
                    f"The configuration file '{self.config_file}' is not valid!"
                )
            return False, errors
        else:
            self.check_dupplicates("topology.section.code")
            self.check_dupplicates("topology.peripheral.pos")
            self.check_dupplicates("simulator.sections.code")
            return True, None

    def get_dir_path(self, path, base_dir=None, check=False):
        """
        Return the full directory of the path with `config_dir` as the base directory.
        """
        return get_dir_path(self.config_dir, path, base_dir, check)

    def get_part(self, path):
        """
        Return a `ConfigPart` object for a part of the configuration
        """
        return ConfigPart(
            self,
            path,
            self.raw_config,
            self.config_dir,
        )

    def __call__(self, path, default=None, type=None, required=True, no_eval=False):
        return self.root(
            path, default=default, type=type, required=required, no_eval=no_eval
        )


class ConfigPart:
    def __init__(self, parent, base_path, config, config_dir):
        self.parent = parent
        self.config_dir = config_dir
        self.base_path = base_path
        if base_path is not None:
            self._config = deep_find(config, base_path)
        else:
            self._config = config

    def get_dir_path(self, path, base_dir=None, check=False):
        return get_dir_path(self.config_dir, path, base_dir, check)

    def path(self, path):
        return "%s.%s" % (self.base_path, path) if self.base_path is not None else path

    def __call__(self, path, default=None, type=None, required=True, no_eval=False):
        return self.value(path, default, type, required, no_eval)

    def value(self, path, default=None, type=None, required=True, no_eval=False):
        required = default is not None and required
        r = default
        if self._config is not None:
            val = reduce(
                lambda di, key: di.get(key, default)
                if isinstance(di, dict)
                else default,
                path.split("."),
                self._config,
            )
            if val == default:
                r = default
            else:
                if not no_eval:
                    if callable(getattr(val, "eval", None)):
                        try:
                            val = val.eval(
                                merge_dicts(
                                    self.parent.custom_functions,
                                    self.parent.scope,
                                )
                            )
                        except Exception as e:
                            raise Exception(
                                "Cannot evaluate Python expression for property '%s'. %s"
                                % (self.path(path), str(e))
                            )
                r = type(val) if type != None else val
        if not r and required:
            raise Exception("The property '%s' does not exist!" % (self.path(path)))
        return r

    def value_str(self, path, default=None, regex=None, required=False):
        v = self.value(path, default=default, type=str, required=required)
        if regex is not None and not re.match(regex, v):
            raise Exception(
                "The property %s value %s does not match %s!"
                % (self.path(path), v, regex)
            )
        return v

    def value_int(self, path, default=None, min=None, max=None, required=False):
        v = self.value(path, default=default, type=int, required=required)
        if min is not None and v < min:
            raise Exception(
                "The property %s value %s must be greater or equal to %d!"
                % (self.path(path), v, min)
            )
        if max is not None and v > max:
            raise Exception(
                "The property %s value %s must be less or equal to %d!"
                % (self.path(path), v, max)
            )
        return v

    def value_bool(self, path, default=None, required=False):
        return self.value(path, default=default, type=bool, required=required)


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_header = "%(asctime)s [%(name)-8.8s] "
    format_msg = "[%(levelname)-1.1s] %(message)s"

    FORMATS = {
        logging.DEBUG: format_header + grey + format_msg + reset,
        logging.INFO: format_header + grey + format_msg + reset,
        logging.WARNING: format_header + yellow + format_msg + reset,
        logging.ERROR: format_header + red + format_msg + reset,
        logging.CRITICAL: format_header + bold_red + format_msg + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def init_logging(
    logs_dir, command_name, log_level="INFO", handlers=["file", "console"]
):
    """
    Initialize the logging, set the log level and logging directory.
    """
    os.makedirs(logs_dir, exist_ok=True)

    # log handlers
    log_handlers = handlers

    # main logs configuration
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "standard": {
                    "format": CustomFormatter.format_header + CustomFormatter.format_msg
                },
                "colored": {"()": CustomFormatter},
            },
            "handlers": {
                "console": {
                    "formatter": "colored" if ANSI_COLORS else "standard",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",  # Default is stderr
                },
                "file": {
                    "formatter": "standard",
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "filename": f"{logs_dir}/ja2mqtt_{command_name}.log",
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 30,
                },
            },
            "loggers": {
                "": {  # all loggers
                    "handlers": log_handlers,
                    "level": f"{log_level}",
                    "propagate": False,
                }
            },
        }
    )


def ja2mqtt_def(config):
    return Config(
        config.get_dir_path(config.root("ja2mqtt")),
        scope=Map(topology=config.root("topology")),
        use_template=True,
    )


def correlation_id(ja2mqtt):
    corrid_field = ja2mqtt("system.correlation_id", None)
    corr_id = randomString(12, letters="abcdef0123456789")
    return corrid_field, corr_id if corrid_field is not None else None
