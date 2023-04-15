# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import click


@click.command("config", help="Show the configuration.")
@click.option(
    "-c",
    "--config",
    "config",
    metavar="<file>",
    is_flag=False,
    required=True,
    help="Configuration file",
)
@click.option(
    "-e",
    "--env",
    "env",
    metavar="<file>",
    is_flag=False,
    required=False,
    help="Environment variable file",
)
@click.option(
    "--ja2mqtt",
    "df",
    is_flag=True,
    required=False,
    help="Show the ja2mqtt definition file",
)
def command_config(config, env, df):
    _config = Config(config, env)
    if not df:
        print(json.dumps(_config.root._config, indent=4, default=str))
    else:
        ja2mqtt_file = _config.get_dir_path(_config.root("ja2mqtt"))
        scope = Map(topology=_config.root("topology"))
        ja2mqtt = Config(ja2mqtt_file, scope=scope, use_template=True)
        print(json.dumps(ja2mqtt.root._config, indent=4, default=str))
