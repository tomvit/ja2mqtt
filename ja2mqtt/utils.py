# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import random
import re
import string
import threading
import time
from functools import reduce


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[32m"
    WARNING = "\033[33m"
    ERROR = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    LIGHTGRAY = "\033[90m"
    MAGENTA = "\033[35m"


def format_str_color(str, color, disable=False):
    color = None if disable else color
    return (
        (color if color is not None else "")
        + str
        + (bcolors.ENDC if color is not None else "")
    )


class PythonExpression:
    def __init__(self, expr):
        self.expr_str = expr
        self.expr = self.compile()

    def compile(self):
        return compile(self.expr_str, "<string>", "eval")

    def eval(self, scope):
        return eval(self.expr, {}, scope)

    def __getstate__(self):
        return (self.expr_str, None)

    def __setstate__(self, state):
        self.expr_str, _ = state
        self.expr = self.compile()

    def __str__(self):
        return "!py %s" % self.expr_str


MAP_IGNORE_KEY_ERROR = True


# *** helper Map object
class Map(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__set_data__(*args, **kwargs)

    def __set_data__(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    if isinstance(v, dict):
                        self[k] = Map(v)
                    else:
                        self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                if isinstance(v, dict):
                    self[k] = Map(v)
                else:
                    self[k] = v

    def __getattr__(self, attr):
        a = self.get(attr)
        if a is None and not MAP_IGNORE_KEY_ERROR:
            raise KeyError(f'The key "{attr}" is undefined!')
        return a

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __delattr__(self, item):
        self.__delitem__(item)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]

    def to_json(self, encoder=None, exclude=[]):
        d = {k: v for k, v in self.__dict__.items() if k not in exclude}
        return json.dumps(d, skipkeys=True, cls=encoder)

    def update(self, map):
        if isinstance(map, Map):
            self.__dict__.update(map.__dict__)
        if isinstance(map, dict):
            self.__dict__.update(map)

    def search(self, callback, item=None, expand=None, data=None):
        if item == None:
            item = self
        if isinstance(item, dict):
            for k, v in item.items():
                if not expand or expand(k):
                    data = self.search(callback, v, expand, callback(k, v, data))
        if isinstance(item, list):
            for v in item:
                data = self.search(callback, v, expand, data)
        return data


def deep_eval(data, scope, raise_ex=False):
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = deep_eval(value, scope, raise_ex)
    elif isinstance(data, list):
        for inx, x in enumerate(data):
            data[inx] = deep_eval(x, scope, raise_ex)
    elif callable(getattr(data, "eval", None)):
        try:
            data = data.eval(scope)
        except Exception as e:
            if raise_ex:
                raise Exception(
                    f"The Python expression '{data.expr_str}' failed. %s." % (str(e))
                )
            else:
                data = None
    return data


def deep_find(dic, keys, default=None, type=None, delim="."):
    val = reduce(
        lambda di, key: di.get(key, default) if isinstance(di, dict) else default,
        keys.split(delim),
        dic,
    )
    if val == default:
        return default
    return type(val) if type != None else val


def import_class(name):
    components = name.split(".")
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def randomString(stringLength=10, letters=None):
    """Generate a random string of fixed length"""
    if letters is None:
        letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


def is_number(s):
    s = str(s)
    p = re.compile(r"^[\+\-]?[0-9]*(\.[0-9]+)?$")
    return s != "" and p.match(s)


def perf_counter(counter=None):
    if counter is None:
        return time.perf_counter()
    else:
        return time.perf_counter() - counter


def deep_merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            if (
                key in destination
                and isinstance(destination[key], list)
                and isinstance(value, list)
            ):
                for x in value:
                    destination[key].append(x)
            else:
                if key not in destination:
                    destination[key] = value
    return destination


def merge_dicts(*dicts):
    result = {}
    for d in dicts:
        if d is not None:
            result.update(d)
    return result


class PathDef:
    def __init__(self, path_def):
        self.path_def = path_def

    def params(self, path):
        path_re = self.path_def

        # find all params in path_def
        params_def = re.findall("(\{[a-zA-Z0-9_\.]+\})", self.path_def)

        # create re pattern by replacing parameters in path_def with pattern to match parameter values
        for p_def in params_def:
            path_re = path_re.replace(p_def, "([a-zA-Z\-0-9\._]+)")

        # get params values
        res = re.findall("^" + path_re + "$", path)
        values = []
        for x in res:
            if type(x) is tuple:
                values.extend(list(x))
            else:
                values.append(x)

        params = Map()
        params.params = Map()
        params.__path_def__ = self.path_def
        params.__path__ = path
        params.replace = self.replace
        for x in range(0, len(params_def)):
            if x < len(values):
                params.params[params_def[x][1:-1]] = str(values[x])
            else:
                # Msg.warn_msg("The path '%s' does not match definition '%s'"%(path, self.path_def))
                return None

        return params

    def replace(self, params, paramsMap):
        new_path = params.__path__
        for k, v in paramsMap.items():
            if params.params.get(k):
                new_path = new_path.replace("%s" % params.params.get(k), v, 1)
            else:
                raise Exception(
                    "The param '%s' has not been found in path definition '%s'."
                    % (k, self.path_def)
                )

        return new_path


def remove_ansi_escape(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def dict_from_string(s, d={}):
    result = d
    parts = s.split("=")
    if len(parts) == 2:
        key = parts[0]
        value = parts[1]
        keys = key.split(".")
        current_dict = result
        for i, k in enumerate(keys):
            if k not in current_dict:
                if i == len(keys) - 1:
                    current_dict[k] = value
                else:
                    current_dict[k] = {}
            current_dict = current_dict[k]
    return result


def str2bool(s):
    if type(s) == str:
        return s.lower() in ["True", "true"]
    else:
        raise Exception(f"Invalid type: {type(s)}")
