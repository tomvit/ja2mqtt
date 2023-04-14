# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import time

from ja2mqtt.config import Config, init_logging

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import __version__ as version
from ja2mqtt.utils import Map

from ja2mqtt.components import Serial, MQTT, SerialMQTTBridge

import click


@click.command("run", help="Run command.")
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
def command_run(config, env):
    config = Config(config, env)

    init_logging(
        config.get_dir_path(config.root.value("logs")),
        "run",
        log_level="DEBUG" if ja2mqtt_config.DEBUG else "INFO",
    )
    log = logging.getLogger("run-loop")

    log.info(f"ja2mqtt, Jablotron JA-121 Serial MQTT bridge, version {version}")

    serial = Serial(config)
    mqtt = MQTT("ja2mqtt-client", config)
    bridge = SerialMQTTBridge(config)

    bridge.set_mqtt(mqtt)
    bridge.set_serial(serial)

    mqtt.start(ja2mqtt_config.exit_event)
    serial.start(ja2mqtt_config.exit_event)

    mqtt.join()
    serial.join()

    log.info("Done.")
