# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

import json
import logging
import sys
import time

import datetime

import click

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt.components import MQTT, SerialMQTTBridge, JA2MQTTConfig
from ja2mqtt.utils import Map, dict_from_string, randomString, format_str_color, bcolors
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


def display_time(epoch_time, time_diff):
    """
    Displays the time in a human readable format.
    :param epoch_time: the time in epoch format
    :param time_diff: if True, the time difference between the current time and the time of the last update is displayed
    :return: the time in a human readable format
    """
    timestamp = datetime.datetime.fromtimestamp(epoch_time)
    if not time_diff:
        return timestamp.strftime("%d-%m-%y %H:%M:%S")

    now = datetime.datetime.now()
    time_diff = now - timestamp

    if time_diff < datetime.timedelta(minutes=1):
        return "just now"
    elif time_diff < datetime.timedelta(hours=1):
        minutes = int(time_diff.total_seconds() / 60)
        if minutes == 1:
            return "1 minute ago"
        else:
            return f"{minutes} minutes ago"
    elif time_diff < datetime.timedelta(hours=6):
        hours = int(time_diff.total_seconds() / 3600)
        if hours == 1:
            return "1 hour ago"
        else:
            return f"{hours} hours ago"
    else:
        return timestamp.strftime("%d-%m-%y %H:%M:%S")


class StatesTable:
    """
    Displays a table with the states of all topics.
    """

    def __init__(self, time_diff=False, sort=False):
        """
        :param time_diff: if True, the time difference between the current time and the time of the last update is displayed
        :param sort: if True, the table is sorted by the time of the last update
        """
        table_def = [
            {"name": "TOPIC", "value": "{topic}"},
            {"name": "UPDATED", "value": "{updated}", "format": self._format_time},
            {"name": "STATE", "value": "{state}", "format": self._format_state},
        ]
        self.table = Table(table_def, None, False)
        self.data = []
        self.displayed = False
        self.time_diff = time_diff
        self.sort = sort

    def _format_state(self, a, b, c):
        """
        Formats the state of a section of a peripheral with a color when ANSI colors are enabled.
        The method displays "OK" and "ARMED" states in green and "READY" state of the section in red.
        """
        if b in ["ON", "ARMED"]:
            return format_str_color(b, bcolors.OKGREEN, not ja2mqtt_config.ANSI_COLORS)
        elif b in ["READY"]:
            return format_str_color(b, bcolors.RED, not ja2mqtt_config.ANSI_COLORS)
        elif b is None:
            return "N/A"
        else:
            return b

    def _format_time(self, a, b, c):
        """
        Formats the time difference between the current time and the time of the last update.
        """
        if b is not None and b != 0:
            try:
                return display_time(b, self.time_diff)
            except Exception as e:
                print(str(e))
        else:
            return "N/A"

    def add(self, topic):
        """
        Adds a new topic to the data.
        """
        self.data.append({"topic": topic.name, "count": 0, "updated": 0, "state": None})

    def topic_data(self, name):
        """
        Returns the index of the topic in the data.
        """
        for inx, d in enumerate(self.data):
            if d["topic"] == name:
                return inx
        return None

    def update(self, topic, data):
        """
        Updates the data of a topic.
        """
        updated = False
        inx = self.topic_data(topic)
        if inx is not None and isinstance(data, dict):
            for k, v in data.items():
                if k in self.data[inx].keys():
                    self.data[inx][k] = v
                    updated = True
        return updated

    def refresh(self):
        """
        Refreshes the table.
        """
        if self.sort:
            data = sorted(self.data, key=lambda x: x["updated"], reverse=True)
        else:
            data = self.data

        if self.displayed:
            if sys.stdout.isatty():
                print("".join(["\033[A" for i in range(len(data) + 2)]))
            else:
                print(
                    f"---- {datetime.datetime.now().strftime('%d-%m-%y %H:%M:%S')} ----"
                )
        self.table.display(data)
        self.displayed = True


@click.command("states", help="Show states of devices.", cls=BaseCommandLogOnly)
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
    "-w",
    "--watch",
    "watch",
    required=False,
    is_flag=True,
    default=False,
    help="Watch states continuously.",
)
@click.option(
    "-t",
    "--time-diff",
    "time_diff",
    required=False,
    is_flag=True,
    default=False,
    help="Display time dfifference for less than 6 hours.",
)
@click.option(
    "-s",
    "--sort",
    "sort",
    required=False,
    is_flag=True,
    default=False,
    help="Sort the data.",
)
def command_states(config, log, data, init_topic, timeout, watch, time_diff, sort):
    states = None

    def _on_message(topic, payload):
        if states.update(topic, Map(json.loads(payload))) and watch:
            states.refresh()

    def _on_connect(client, userdata, flags, rc):
        for d in states.data:
            client.subscribe(d["topic"])

    # configuration
    ja2mqtt = JA2MQTTConfig(config)
    if init_topic is not None and not ja2mqtt.topic_exists(init_topic):
        raise Exception(f"The topic {init_topic} does not exist!")

    # states table
    states = StatesTable(time_diff, sort)
    for topic in ja2mqtt.topics_serial2mqtt:
        if not topic.disabled:
            # only topics with `state` property in data payload
            if len([x for x in [r.write for r in topic.rules] if "state" in x]) > 0:
                states.add(topic)
    if watch:
        states.refresh()

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
        click.echo("Waiting for states to be updated...")
        time.sleep(ja2mqtt.correlation_timeout if timeout is None else timeout)
        states.refresh()
    else:
        try:
            while not ja2mqtt_config.exit_event.is_set():
                ja2mqtt_config.exit_event.wait(60)
                states.refresh()
        finally:
            ja2mqtt_config.exit_event.set()
