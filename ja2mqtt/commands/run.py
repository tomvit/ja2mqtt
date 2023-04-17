# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import logging
import time

import click

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import get_version_string
from ja2mqtt.components import MQTT, Serial, SerialMQTTBridge
from ja2mqtt.config import Config, init_logging
from ja2mqtt.utils import Map, randomString

from . import BaseCommand


@click.command("run", help="Run command.", cls=BaseCommand)
def command_run(config, log):
    serial = Serial(config)
    mqtt = MQTT(f"ja2mqtt-client+{randomString(10)}", config)
    bridge = SerialMQTTBridge(config)

    bridge.set_mqtt(mqtt)
    bridge.set_serial(serial)

    mqtt.start(ja2mqtt_config.exit_event)
    serial.start(ja2mqtt_config.exit_event)

    mqtt.join()
    serial.join()

    log.info("Done.")
