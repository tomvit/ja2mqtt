# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import logging

import click
from click import Option

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import __version__
from ja2mqtt.config import Config, init_logging


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

    def init_logging(self, config):
        init_logging(
            config.get_dir_path(config.root("logs")),
            "run",
            log_level="DEBUG" if ja2mqtt_config.DEBUG else "INFO",
        )

    def validate_config(self, config):
        config.validate()

    def invoke(self, ctx):
        config_file = ctx.params.pop("config")
        env_file = ctx.params.pop("env")
        config = Config(config_file, env_file, schema="config-schema.yaml")
        self.validate_config(config)

        self.init_logging(config)
        log = logging.getLogger(ctx.command.name + "-loop")
        log.info(f"ja2mqtt, Jablotron JA-121 Serial MQTT bridge, version {__version__}")

        ctx.params["config"] = config
        ctx.params["log"] = log
        super().invoke(ctx)


class BaseCommandLogOnly(BaseCommand):
    def init_logging(self, config):
        init_logging(
            config.get_dir_path(config.root("logs")),
            "run",
            log_level="DEBUG" if ja2mqtt_config.DEBUG else "INFO",
            handlers=["file"],
        )


class BaseCommandLogOnlyNoValidate(BaseCommandLogOnly):
    def validate_config(self, config):
        pass
