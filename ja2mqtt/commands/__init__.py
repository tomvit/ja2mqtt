# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import logging

import click
from click import Option

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import get_version_string
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
            ),
        )
        self.params.insert(
            0,
            Option(
                ("-e", "--env"),
                metavar="<file>",
                required=False,
                help="Environment variable file",
            ),
        )

    def init_logging(self, config):
        init_logging(
            config.get_dir_path(config.root("logs")),
            "run",
            log_level="DEBUG" if ja2mqtt_config.DEBUG else "INFO",
        )

    def invoke(self, ctx):
        config_file = ctx.params.pop("config")
        env_file = ctx.params.pop("env")
        config = Config(config_file, env_file)

        self.init_logging(config)
        log = logging.getLogger(ctx.command.name + "-loop")
        log.info(
            f"ja2mqtt, Jablotron JA-121 Serial MQTT bridge, version {get_version_string()}"
        )

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


@click.group()
@click.option(
    "--no-ansi",
    "no_ansi",
    is_flag=True,
    default=False,
    help="Do not use ANSI colors",
)
@click.option(
    "--debug",
    "debug",
    is_flag=True,
    default=False,
    help="Print debug information",
)
@click.version_option(version=get_version_string())
def ja2mqtt(no_ansi, debug):
    if no_ansi:
        ja2mqtt_config.ANSI_COLORS = False
    if debug:
        ja2mqtt_config.DEBUG = True


from .config import command_config
from .run import command_run
from .test import command_publish

ja2mqtt.add_command(command_run)
ja2mqtt.add_command(command_config)
ja2mqtt.add_command(command_publish)
