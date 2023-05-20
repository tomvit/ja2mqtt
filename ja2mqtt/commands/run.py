# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

import click
import pidfile
import os

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt.components import MQTT, Serial, SerialMQTTBridge, Simulator
from ja2mqtt.utils import randomString

from ja2mqtt import __version__

from . import RunCommand


@click.command("run", help="Run command.", cls=RunCommand)
def command_run(config, log):
    with pidfile.PIDFile(ja2mqtt_config.PID_FILE):
        bridge = SerialMQTTBridge(config)

        log.info(f"ja2mqtt, Jablotron JA-121 Serial MQTT bridge, version {__version__}")

        simulator = None
        if config("simulator") is not None:
            simulator = Simulator(config.get_part("simulator"), bridge.prfstate_bits)
        elif config("serial.use_simulator", True):
            log.error("The serial interface is set to be simulated but the simulator configuration does not exist!")

        serial = Serial(config.get_part("serial"), simulator)
        mqtt = MQTT(f"ja2mqtt-server+{bridge.topic_prefix}", config.get_part("mqtt-broker"))

        bridge.set_mqtt(mqtt)
        bridge.set_serial(serial)

        for x in (mqtt, serial, bridge):
            x.start(ja2mqtt_config.exit_event)

        for x in (mqtt, serial, bridge):
            x.join()

        log.info("Done.")


@click.command("stop", help="Stop running ja2mqtt process.")
def command_stop():
    """
    Stop running ja2mqtt process.
    """
    p = pidfile.PIDFile(ja2mqtt_config.PID_FILE)
    if not p.is_running:
        raise Exception("ja2mqtt process is not running.")

    with open(p._file, "r") as f:
        try:
            pid = int(f.read())
            click.echo(f"Stopping ja2mqtt process with pid={pid}.")
            os.kill(pid, 15)
        except (OSError, ValueError) as e:
            raise Exception(f"Cannot stop ja2mqtt process. {str(e)}")
