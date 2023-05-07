# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json
import logging
import os
import re
import threading
import time
from queue import Queue

import paho.mqtt.client as mqtt
import serial as py_serial

from ja2mqtt.config import Config, ENCODING
from ja2mqtt.utils import Map, PythonExpression, deep_eval, deep_merge, merge_dicts

from . import Component
from .simulator import Simulator


class SerialJA121TException(Exception):
    pass


def decode_prfstate(prfstate):
    """
    Decode prfstate from a hexadecimal string to a dictionary, where the keys
    represent the peripheral IDs and the values represent the state (ON/OFF)
    of the respective peripherals. For details see JA-121T documentation.
    """
    try:
        parts = [
            bin(int(prfstate[i : i + 2], 16))[2:].zfill(8)
            for i in range(0, len(prfstate), 2)
        ]

        peripherals = {}
        for x in range(0, int(len(prfstate) / 2)):
            j = 0
            for y in range(x * 8 + 7, x * 8 - 1, -1):
                peripherals[y] = parts[x][j]
                j += 1

        return {
            str(k): ("ON" if peripherals[k] == "1" else "OFF")
            for k in sorted(peripherals.keys())
        }
    except Exception as e:
        raise SerialJA121TException(
            f"Cannot decode prfstate string {prfstate}. {str(e)}"
        )


def encode_prfstate(prf, prf_state_bits=24):
    """
    Encode prfstate from the prf state object. This is an inverse funtion to decode_prfstate,
    i.e. it must hold that `encode_prfstate(decode_prfstate(X)) == X`
    """
    b = "".zfill(prf_state_bits)
    for p in prf.keys():
        if prf[p] == "ON":
            index = int(p)
            b = b[:index] + "1" + b[index + 1 :]
    r = ""
    for x in range(len(b) // 8):
        h = hex(int(b[x * 8 : x * 8 + 8][::-1], 2))
        h2 = h[2:].upper().zfill(2)
        r += h2
    return r


class Serial(Component):
    """
    Serial provides an interface for the serial port where JA-121T is connected.
    """

    def __init__(self, config, simulator):
        """
        Initialize the serial object. It reads configuration parameters from the config
        and creates `ser` object that can be either `PySerial` or `Simulator` based on the
        `use_simulator` property in the configuration.
        """
        super().__init__(config, "serial")
        self.buffer = Queue()
        self.wait_on_ready = self.config.value_int("wait_on_ready", default=10)
        self.use_simulator = self.config.value_bool("use_simulator", default=False)
        if not self.use_simulator:
            self.ser = None
            self.port = self.config.value_str("port", required=True)
            self.log.info(f"The serial connection configured, the port is {self.port}")
        else:
            self.port = "<simulator>"
            self.ser = simulator
            self.log.info("The serial interface events will be simulated.")
            self.log.debug(f"The simulator object is {self.ser}")

    def create_serial(self):
        """
        Create serial object and initialize the parameters from the configuration.
        """
        self.ser = py_serial.serial_for_url(self.port, do_not_open=True)
        self.ser.baudrate = self.config.value_int("baudrate", min=0, default=9600)
        self.ser.bytesize = self.config.value_int("bytesize", min=7, max=8, default=8)
        self.ser.parity = self.config.value_str("parity", default="N")
        self.ser.stopbits = self.config.value_int("stopbits", default=1)
        self.ser.rtscts = self.config.value_bool("rtscts", default=False)
        self.ser.xonxoff = self.config.value_bool("xonxoff", default=False)
        self.ser.timeout = 1
        self.log.debug(f"The serial object created: {self.ser}")

    def is_ready(self):
        """
        Retrun True if the serial object exist.
        """
        return self.ser is not None

    def open(self, exit_event):
        """
        Open serial interface. If the interface cannot be opened due to an error,
        try opening it with frequency of `wait_on_ready` parameter.
        """
        if self.ser is None:
            self.log.info(f"Opening serial port {self.port}")
            while not exit_event.is_set():
                try:
                    if not os.path.exists(self.port):
                        raise SerialJA121TException(
                            f"The port {self.port} does not exist in the system. Is it connected?"
                        )
                    self.create_serial()
                    self.ser.open()
                    break
                except Exception as e:
                    self.log.error(str(e))
                    self.log.info(
                        f"Waiting {self.wait_on_ready} seconds for the port to be ready..."
                    )
                    exit_event.wait(self.wait_on_ready)
                    self.ser = None

    def close(self):
        """
        Close the serial port when it is open.
        """
        if self.ser is not None:
            self.log.info(f"Closing serial port {self.port}")
            try:
                self.ser.close()
            except Exception as e:
                self.log.error(f"Cannot close the serial port {self.port}. {str(e)}")
            self.ser = None

    def writeline(self, line):
        """
        Write a single line of string to the seiral port. It convers the string to bytes using
        the defined `encoding` and adds a LF at the end.
        """
        self.log.debug(f"Writing to serial: {line}")
        try:
            self.ser.write(bytes(line + "\n", ENCODING))
        except Exception as e:
            self.log.error(str(e))

    def worker(self, exit_event):
        """
        The main worker of the serial object that reads data from the serial port and
        puts them to the queue `buffer`. Althoguh the `worker` method (that only reads
        the data from the serial port) can run in parallel with the `writeline` method,
        due to the "global interpreter lock" they both should be thread-safe.
        """
        self.open(exit_event)
        try:
            while not exit_event.is_set():
                try:
                    x = self.ser.readline()
                except Exception as e:
                    self.log.error(
                        f"Error occured while reading data from the serial port. {str(e)}"
                    )
                    self.close()
                    self.open(exit_event)
                    continue
                try:
                    data_str = x.decode(ENCODING).strip("\r\n").strip()
                    if data_str != "":
                        self.log.debug(f"Received data from serial: {data_str}")
                        self.buffer.put(data_str)
                except UnicodeDecodeError as e:
                    self.log.error(str(e))
                    continue
                else:
                    # this is necessary to allow other threads to run too
                    exit_event.wait(0.2)
        finally:
            self.close()
            self.log.info("Serial worker ended.")

    def start(self, exit_event):
        """
        Start the worker thread of the serial object. If the simulator is used, this also starts
        the worker thread of the simulator object.
        """
        super().start(exit_event)
        if self.use_simulator and isinstance(self.ser, Simulator):
            self.ser.start(exit_event)

    def join(self):
        """
        Join the worker thread and simulator thread if it exists.
        """
        super().join()
        if self.use_simulator and isinstance(self.ser, Simulator):
            self.ser.join()
