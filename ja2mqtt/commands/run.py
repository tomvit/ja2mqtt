# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import logging
import time

import click

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt.components import MQTT, Serial, SerialMQTTBridge, Simulator
from ja2mqtt.config import Config, init_logging
from ja2mqtt.utils import Map, randomString

from . import BaseCommand


@click.command("run", help="Run command.", cls=BaseCommand)
def command_run(config, log):
    bridge = SerialMQTTBridge(config)
    simulator = Simulator(config.get_part("simulator"), bridge.prfstate_bits)
    serial = Serial(config.get_part("serial"), simulator)
    mqtt = MQTT(f"ja2mqtt-client+{randomString(10)}", config.get_part("mqtt-broker"))

    bridge.set_mqtt(mqtt)
    bridge.set_serial(serial)

    for x in (mqtt, serial, bridge):
        x.start(ja2mqtt_config.exit_event)

    for x in (mqtt, serial, bridge):
        x.join()

    log.info("Done.")
