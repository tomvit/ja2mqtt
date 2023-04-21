# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json
import os

import click

from ja2mqtt.config import Config, env_variables
from ja2mqtt.utils import Map

from . import BaseCommandLogOnly


@click.group("config", help="Configuration commands")
def command_config():
    pass


@click.command("main", help="Show the main configuration.", cls=BaseCommandLogOnly)
def config_main(config, log):
    print(json.dumps(config.root._config, indent=4, default=str))


@click.command(
    "ja2mqtt", help="Show the ja2mqtt definition configuration.", cls=BaseCommandLogOnly
)
def config_ja2mqtt(config, log):
    ja2mqtt_file = config.get_dir_path(config.root("ja2mqtt"))
    scope = Map(topology=config.root("topology"))
    ja2mqtt = Config(ja2mqtt_file, scope=scope, use_template=True)
    print(json.dumps(ja2mqtt.root._config, indent=4, default=str))


@click.command("env", help="Show environment varialbes.")
def config_env():
    print("List of environment variables used by ja2mqtt:")
    print("")
    for e in env_variables:
        print(f"{e}={os.getenv(e)}")
    print("")

@click.command("topics", help="Show MQTT topics.", cls=BaseCommandLogOnly)
def config_topics(config, log):
    ja2mqtt_file = config.get_dir_path(config.root("ja2mqtt"))
    scope = Map(topology=config.root("topology"))
    ja2mqtt = Config(ja2mqtt_file, scope=scope, use_template=True)

    print("Publishing:")
    for t in ja2mqtt("serial2mqtt"):
        print(f"- {t['name']}")
    print("Subscribing:")
    for t in ja2mqtt("mqtt2serial"):
        print(f"- {t['name']}")


command_config.add_command(config_main)
command_config.add_command(config_ja2mqtt)
command_config.add_command(config_env)
command_config.add_command(config_topics)
