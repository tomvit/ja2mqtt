# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import json
import logging
import threading
import re

import serial as py_serial
import paho.mqtt.client as mqtt

from ja2mqtt.utils import (
    Map,
    merge_dicts,
    deep_eval,
    deep_merge,
    PythonExpression,
)
from ja2mqtt.config import Config
from .simulator import Simulator
from queue import Queue

from . import Component

class Serial(Component):
    """
    Serial provides an interface for the serial port where JA-121T is connected.
    """

    def __init__(self, config):
        super().__init__(config.get_part("serial"), "serial")
        self.encoding = self.config.value_bool("encoding", default="ascii")
        self.use_simulator = self.config.value_bool("use_simulator", default=False)
        if not self.use_simulator:
            self.port = self.config.value_str("port", required=True)
            self.ser = py_serial.serial_for_url(
                self.port, do_not_open=True
            )
            self.ser.baudrate = self.config.value_int("baudrate", min=0, default=9600)
            self.ser.bytesize = self.config.value_int(
                "bytesize", min=7, max=8, default=8
            )
            self.ser.parity = self.config.value_str("parity", default="N")
            self.ser.stopbits = self.config.value_int("stopbits", default=1)
            self.ser.rtscts = self.config.value_bool("rtscts", default=False)
            self.ser.xonxoff = self.config.value_bool("xonxoff", default=False)
            self.log.info(
                f"The serial connection configured, the port is {self.ser.port}"
            )
            self.log.debug(f"The serial object is {self.ser}")
        else:
            self.port = "<__simulator__>"
            self.ser = Simulator(config.get_part("simulator"), self.encoding)
            self.log.info(
                "The simulation is enabled, events will be simulated. The serial interface is not used."
            )
            self.log.debug(f"The simulator object is {self.ser}")
        self.ser.timeout = 1
        self.on_data_ext = None

    def on_data(self, data):
        self.log.debug(f"Received data from serial: {data}")
        if self.on_data_ext is not None:
            self.on_data_ext(data)

    def open(self):
        self.log.info(f"Opening serial port {self.port}")
        self.ser.open()

    def close(self):
        self.log.info(f"Closing serial port {self.port}")
        self.ser.close()

    def writeline(self, line):
        self.log.debug(f"Writing to serial: {line}")
        try:
            self.ser.write(bytes(line + "\n", self.encoding))
        except Exception as e:
            self.log.error(str(e))

    def worker(self, exit_event):
        self.open()
        try:
            while not exit_event.is_set():
                x = self.ser.readline()
                data_str = x.decode(self.encoding).strip("\r\n").strip()
                if data_str != "":
                    self.on_data(data_str)
                exit_event.wait(0.2)
        finally:
            self.close()
            self.log.info("Serial worker ended.")

    def start(self, exit_event):
        super().start(exit_event)
        if self.use_simulator and isinstance(self.ser, Simulator):
            self.ser.start(exit_event)

    def join(self):
        super().join()
        if self.use_simulator and isinstance(self.ser, Simulator):
            self.ser.join()
