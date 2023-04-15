# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json

import click

from ja2mqtt.config import Config
from ja2mqtt.utils import Map

from . import BaseCommandLogOnly


@click.command("config", help="Show the configuration.", cls=BaseCommandLogOnly)
@click.option(
    "--ja2mqtt",
    "df",
    is_flag=True,
    required=False,
    help="Show the ja2mqtt definition file",
)
def command_config(config, df, log):
    if not df:
        print(json.dumps(config.root._config, indent=4, default=str))
    else:
        ja2mqtt_file = config.get_dir_path(config.root("ja2mqtt"))
        scope = Map(topology=config.root("topology"))
        ja2mqtt = Config(ja2mqtt_file, scope=scope, use_template=True)
        print(json.dumps(ja2mqtt.root._config, indent=4, default=str))
