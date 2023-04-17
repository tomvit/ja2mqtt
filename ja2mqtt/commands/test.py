# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json
import logging
import time

import click

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import __version__ as version
from ja2mqtt.components import MQTT
from ja2mqtt.config import Config, init_logging, ja2mqtt_def
from ja2mqtt.utils import Map, dict_from_string, randomString

from . import BaseCommandLogOnly


@click.command("pub", help="Publish a ja2mqtt topic in MQTT.", cls=BaseCommandLogOnly)
@click.option(
    "-t",
    "--topic",
    "topic",
    metavar="<name>",
    is_flag=False,
    required=True,
    help="Topic name to be published",
)
@click.option(
    "-d",
    "--data",
    "data",
    multiple=True,
    metavar="<d1 d2 ...>",
    required=False,
    help="Data as a key=value pair",
)
def command_publish(config, topic, data, log):
    ja2mqtt = ja2mqtt_def(config)
    _topic = next(filter(lambda x: x["name"] == topic, ja2mqtt("mqtt2serial")), None)
    if _topic is None:
        raise Exception(
            f"The topic with name '{topic}' does not exist in the ja2mqtt definition file!"
        )

    _data = {}
    for d in data:
        _data = dict_from_string(d, _data)

    cor_id = ja2mqtt("options.correlation_id", None)
    if cor_id is not None:
        _data[cor_id] = randomString(12, letters="abcdef0123456789")

    mqtt = MQTT(f"ja2mqtt-test-{randomString(5)}", config)
    mqtt.start(ja2mqtt_config.exit_event)
    try:
        mqtt.wait_is_connected(ja2mqtt_config.exit_event)
        mqtt.publish(_topic["name"], json.dumps(_data))
    finally:
        ja2mqtt_config.exit_event.set()
