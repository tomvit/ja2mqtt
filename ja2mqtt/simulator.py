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

from queue import Queue, Empty


class Section:
    def __init__(self, data):
        self.code = data.code
        self.state = data.state

    def __str__(self):
        return f"STATE {self.code} {self.state}"

    def set(self):
        if self.state == "ARMED":
            return "OK"
        if self.state == "READY":
            self.state = "ARMED"
            return self.__str__()

    def unset(self):
        if self.state == "READY":
            return "OK"
        if self.state == "ARMED":
            self.state = "READY"
            return self.__str__()


class Simulator():
    def __init__(self, config, encoding):
        self.log = logging.getLogger("simulator")
        self.config = config
        self.response_delay = config.value_int("response_delay", default=0.5)
        self.rules = [Map(x) for x in config.value("rules")]
        self.sections = {
            str(x["code"]): Section(Map(x)) for x in config.value("sections")
        }
        self.pin = config.value("pin")
        self.timeout = None
        self.buffer = Queue()
        self.encoding = encoding

    def open(self):
        pass

    def close(self):
        pass

    def _add_to_buffer(self, data):
        time.sleep(self.response_delay)
        self.buffer.put(data)

    def write(self, data):
        def _match(pattern, data_str):
            m = re.compile(pattern).match(data_str)
            if m:
                return Map(m.groupdict())
            else:
                return None

        def _check_pin(command):
            if command.pin != str(self.pin):
                self._add_to_buffer("ERROR: 3 NO_ACCESS")
                return False
            return True

        data_str = data.decode(self.encoding).strip("\n")

        # SET and UNSET commands
        command = _match(
            "^(?P<pin>[0-9]+) (?P<command>SET|UNSET) (?P<code>[0-9]+)$",
            data_str,
        )
        if command is not None and _check_pin(command):
            section = self.sections.get(command.code)
            if section is not None:
                data = {
                    "SET": lambda: section.set(),
                    "UNSET": lambda: section.unset(),
                }[command.command]()
                self._add_to_buffer(data)
            else:
                self._add_to_buffer("ERROR: 4 INVALID_VALUE")

        # STATE command
        command = _match("^(?P<pin>[0-9]+) (?P<command>STATE)$", data_str)
        if command is not None and _check_pin(command):
            time.sleep(self.response_delay)
            for section in self.sections.values():
                self.buffer.put(str(section))

    def readline(self):
        try:
            return bytes(self.buffer.get(timeout=self.timeout), self.encoding)
        except Empty:
            return b""

    def worker(self, exit_event):
        while not exit_event.is_set():
            for rule in self.rules:
                if rule.get("time"):
                    if rule.__last_write is None:
                        rule.__last_write = time.time()
                    if time.time() - rule.__last_write > rule.time:
                        self.buffer.put(rule.write)
                        rule.__last_write = time.time()
            exit_event.wait(1)

    def start(self, exit_event):
        threading.Thread(target=self.worker, args=(exit_event,), daemon=True).start()
