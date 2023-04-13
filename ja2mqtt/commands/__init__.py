# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import click

from .run import run
from .config import config

import ja2mqtt.config as ja2mqtt_config


@click.group()
@click.option(
    "--no-ansi", "no_ansi", is_flag=True, default=False, help="Do not use ANSI colors"
)
@click.option(
    "--debug", "debug", is_flag=True, default=False, help="Print debug information"
)
def ja2mqtt(no_ansi, debug):
    if no_ansi:
        ja2mqtt_config.ANSI_COLORS = False
    if debug:
        ja2mqtt_config.DEBUG = True


ja2mqtt.add_command(run)
ja2mqtt.add_command(config)
