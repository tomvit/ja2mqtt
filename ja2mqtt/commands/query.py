# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json
import logging
import sys
import time

from datetime import datetime

import click

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import __version__ as version
from ja2mqtt.components import MQTT, SerialMQTTBridge, JA2MQTTConfig
from ja2mqtt.config import Config, init_logging
from ja2mqtt.utils import Map, dict_from_string, randomString
from ja2mqtt.json2table import Table

from . import BaseCommandLogOnly


@click.command("pub", help="Publish a topic.", cls=BaseCommandLogOnly)
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
    bridge = SerialMQTTBridge(config)
    _topic = next(filter(lambda x: x.name == topic, bridge.topics_mqtt2serial), None)
    if _topic is None:
        raise Exception(
            f"The topic with name '{topic}' does not exist in the ja2mqtt definition file!"
        )

    _data = {}
    for d in data:
        _data = dict_from_string(d, _data)

    field, id = bridge.corr_id()
    if field is not None:
        _data[field] = id

    def _wait_for_response(topic, payload):
        data = Map(json.loads(payload))
        if field is None or data.get(field) == id:
            print(f"--> recv: {topic}: {payload}")

    def _on_connect(client, userdata, flags, rc):
        for topic in bridge.topics_serial2mqtt:
            client.subscribe(topic.name)

    mqtt = MQTT(f"ja2mqtt-test-{randomString(5)}", config.get_part("mqtt-broker"))
    mqtt.on_message_ext = _wait_for_response
    mqtt.on_connect_ext = _on_connect
    mqtt.start(ja2mqtt_config.exit_event)
    try:
        mqtt.wait_is_connected(ja2mqtt_config.exit_event)
        print(f"<-- send: {_topic.name}: {json.dumps(_data)}")
        mqtt.publish(_topic.name, json.dumps(_data))
        time.sleep(bridge.correlation_timeout if timeout is None else timeout)
    finally:
        ja2mqtt_config.exit_event.set()


class StatsTable():
    def __init__(self):
        table_def = [
            {"name": "TOPIC", "value": "{topic}"},
            {"name": "UPDATED", "value": "{updated}", "format": self._format_time},
            {"name": "STATE", "value": "{state}"},
            {"name": "COUNT", "value": "{count}"},
        ]
        self.table = Table(table_def, None, False)
        self.data = []
        self.displayed = False

    def _format_time(self, a, b, c):
        if b is not None:
            return datetime.fromtimestamp(b).strftime("%d-%m-%Y %H:%M:%S")
        else:
            return "N/A"

    def add(self, topic):
        self.data.append({"topic": topic.name, "count": 0, "updated": None, "state": None})

    def topic_data(self, name):
        for inx, d in enumerate(self.data):
            if d["topic"] == name:
                return inx
        return None

    def update(self, topic, data):
        updated = False
        inx = self.topic_data(topic)
        if inx is not None and isinstance(data, dict):
            for k,v in data.items():
                if k in self.data[inx].keys():
                    # print(topic, k, self.data[inx][k], v)
                    self.data[inx][k] = v
                    updated = True
        return updated

    def refresh(self):
        if self.displayed and sys.stdout.isatty():
            print("".join(["\033[A" for i in range(len(self.data) + 2)]))
        self.table.display(self.data)
        self.displayed = True


@click.command(
    "stats", help="Subscribe to topics and display stats.", cls=BaseCommandLogOnly
)
@click.option(
    "-i",
    "--init",
    "init_topic",
    metavar="<name>",
    is_flag=False,
    required=False,
    help="The initi topic name to be published.",
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
@click.option(
    "--watch", "-w"
    "watch",
    required=False,
    is_flag=True,
    default=False,
    help="Watch stats continuously.",
)
def command_stats(config, log, data, init_topic, timeout, watch):

    stats = None

    def _on_message(topic, payload):
        if stats.update(topic, Map(json.loads(payload))) and watch:
            stats.refresh()

    def _on_connect(client, userdata, flags, rc):
        for d in stats.data:
            client.subscribe(d["topic"])

    # configuration
    ja2mqtt = JA2MQTTConfig(config)
    if init_topic is not None and not ja2mqtt.topic_exists(init_topic):
        raise Exception(f"The topic {init_topic} does not exist!")

    # stats table
    stats = StatsTable()
    for topic in ja2mqtt.topics_serial2mqtt:
        if not topic.disabled:
            stats.add(topic)
    if watch:
        stats.refresh()

    # mqtt client
    mqtt = MQTT(f"ja2mqtt-test-{randomString(5)}", config.get_part("mqtt-broker"))
    mqtt.on_message_ext = _on_message
    mqtt.on_connect_ext = _on_connect
    mqtt.start(ja2mqtt_config.exit_event)
    mqtt.wait_is_connected(ja2mqtt_config.exit_event)

    # get all states
    if init_topic is not None:
        _data = {}
        for d in data:
            _data = dict_from_string(d, _data)
        mqtt.publish(init_topic, json.dumps(_data))

    if not watch:
        click.echo("Waiting for stats to be updated...")
        time.sleep(ja2mqtt.correlation_timeout if timeout is None else timeout)
        stats.refresh()
    else:
        try:
            while not ja2mqtt_config.exit_event.is_set():
                ja2mqtt_config.exit_event.wait(5)
        finally:
            ja2mqtt_config.exit_event.set()
