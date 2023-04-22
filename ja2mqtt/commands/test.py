# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json
import logging
import sys
import time

import click

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import __version__ as version
from ja2mqtt.components import MQTT
from ja2mqtt.config import Config, correlation_id, init_logging, ja2mqtt_def
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
@click.option(
    "--timeout",
    "timeout",
    metavar="<timeout>",
    required=False,
    type=float,
    help="Timeout to wait for responses. The default is correlation timeout from the ja2mqtt configuration.",
)
def command_publish(config, topic, data, log, timeout):
    ja2mqtt = ja2mqtt_def(config)
    _topic = next(filter(lambda x: x["name"] == topic, ja2mqtt("mqtt2serial")), None)
    if _topic is None:
        raise Exception(
            f"The topic with name '{topic}' does not exist in the ja2mqtt definition file!"
        )

    _data = {}
    for d in data:
        _data = dict_from_string(d, _data)

    field, id = correlation_id(ja2mqtt.root)
    if field is not None:
        _data[field] = id

    def _wait_for_response(topic, payload):
        data = Map(json.loads(payload))
        if field is None or data.get(field) == id:
            print(f"--> recv: {topic}: {payload}")

    def _on_connect(client, userdata, flags, rc):
        for topic in ja2mqtt.root("serial2mqtt"):
            client.subscribe(topic["name"])

    mqtt = MQTT(f"ja2mqtt-test-{randomString(5)}", config.get_part("mqtt-broker"))
    mqtt.on_message_ext = _wait_for_response
    mqtt.on_connect_ext = _on_connect
    mqtt.start(ja2mqtt_config.exit_event)
    try:
        mqtt.wait_is_connected(ja2mqtt_config.exit_event)
        print(f"<-- send: {_topic['name']}: {json.dumps(_data)}")
        mqtt.publish(_topic["name"], json.dumps(_data))
        time.sleep(
            ja2mqtt.root("system.correlation_timeout", 1.5)
            if timeout is None
            else timeout
        )
    finally:
        ja2mqtt_config.exit_event.set()
