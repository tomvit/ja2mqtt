# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

import logging

import os
import sys
import click
import pidfile
from click import Option

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt.config import Config, init_logging, PID_FILE

class BaseCommand(click.core.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params.insert(
            0,
            Option(
                ("-c", "--config"),
                metavar="<file>",
                required=True,
                help="Configuration file",
                default=ja2mqtt_config.CONFIG_FILE,
            ),
        )
        self.params.insert(
            0,
            Option(
                ("-e", "--env"),
                metavar="<file>",
                required=False,
                help="Environment variable file",
                default=ja2mqtt_config.CONFIG_ENV,
            ),
        )
        self.log = None

    def init_logging(self, config, command_name):
        init_logging(
            config.get_dir_path(config.root("logs")),
            command_name,
            log_level="DEBUG" if ja2mqtt_config.DEBUG else "INFO",
        )

    def validate_config(self, config):
        config.validate()

    def command_run(self, ctx):
        config_file = ctx.params.pop("config")
        env_file = ctx.params.pop("env")
        config = Config(config_file, env_file, schema="config-schema.yaml")
        self.validate_config(config)

        self.init_logging(config, ctx.command.name)
        self.log = logging.getLogger(ctx.command.name + "-loop")

        ctx.params["config"] = config
        ctx.params["log"] = self.log

    def invoke(self, ctx):
        self.command_run(ctx)
        super().invoke(ctx)


class RunCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params.insert(
            0,
            Option(
                ("-d", "--daemon"),
                required=False,
                help="Run as daemon",
                default=False,
                is_flag=True,
            ),
        )
        self.is_daemon = False

    def init_logging(self, config, command_name):
        handlers = ["file"]
        if not self.is_daemon:
            handlers.append("console")
        init_logging(
            config.get_dir_path(config.root("logs")),
            command_name + ("" if not self.is_daemon else "_daemon"),
            log_level="DEBUG" if ja2mqtt_config.DEBUG else "INFO",
            handlers=handlers,
        )

    def command_run(self, ctx):
        if pidfile.PIDFile(ja2mqtt_config.PID_FILE).is_running:
            raise Exception(f"The {PID_FILE} already exists. Is ja2mqtt already running?")
        
        self.is_daemon = ctx.params.pop("daemon")
        super().command_run(ctx)
        if self.is_daemon:
            pid = os.fork()
            if pid == 0:
                os.setsid()
                os.close(0)
                os.close(1)
                os.close(2)
                self.log.debug(f"Running ja2mqtt as daemon.")
            else:
                self.log.debug(f"Exiting the current process and starting the daemon process (pid={pid}).")
                ja2mqtt_config.exit_event.set()
                sys.exit(0)


class BaseCommandLogOnly(BaseCommand):
    def init_logging(self, config, command_name):
        init_logging(
            config.get_dir_path(config.root("logs")),
            command_name,
            log_level="DEBUG" if ja2mqtt_config.DEBUG else "INFO",
            handlers=["file"],
        )


class BaseCommandLogOnlyNoValidate(BaseCommandLogOnly):
    def validate_config(self, config):
        pass
