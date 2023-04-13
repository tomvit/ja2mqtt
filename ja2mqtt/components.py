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

from ja2mqtt.utils import Map, merge_dicts, deep_eval, deep_merge, PythonExpression
from ja2mqtt.config import Config

class Component():
    def __init__(self, config, name):
        self.log = logging.getLogger(name)
        self.config = config
        self.name = name

    def worker(self, exit_event):
        pass

    def start(self, exit_event):
        threading.Thread(
            target=self.worker, args=(exit_event,), daemon=True
        ).start()


class Serial(Component):
    """
    Serial provides an interface for the serial port where JA-121T is connected.
    """

    def __init__(self, config):
        super().__init__(config, "serial")
        self.ser = py_serial.serial_for_url(
            config.value_str("port", required=True), do_not_open=True
        )
        self.log.info(f"The serial port is {self.ser.port}")
        self.ser.baudrate = config.value_int("baudrate", min=0, default=9600)
        self.ser.bytesize = config.value_int("bytesize", min=7, max=8, default=8)
        self.ser.parity = config.value_str("parity", default="N")
        self.ser.stopbits = config.value_int("stopbits", default=1)
        self.ser.rtscts = config.value_bool("rtscts", default=False)
        self.ser.xonxoff = config.value_bool("xonxoff", default=False)
        self.ser.timeout = 1
        self.encoding = config.value_bool("encoding", default='ascii')
        self.simulator = config.value_bool("simulator", default=False)
        self.log.debug(f"The serial object is {self.ser}")

    def on_data(self, data):
        pass

    def open(self):
        if not self.simulator:
            self.ser.open()

    def close(self):
        if not self.simulator:
            self.ser.close()

    def writeline(self, line):
        if not self.simulator:
            self.ser.write(bytes(line + "\n", self.encoding))

    def worker(self, exit_event):
        self.open()
        try:
            while not exit_event.is_set():
                if not self.simulator:
                    x = self.ser.readline()
                    if x != b'':
                        self.on_data(x.decode(self.encoding).strip("\r\n"))
                else:
                    if int(time.time()) % 11 == 10:
                        self.on_data('OK')
                    if int(time.time()) % 11 == 6:
                        self.on_data('ERROR 4: NO_ACCESS')
                exit_event.wait(0.2)
        finally:
            self.close()


class MQTT(Component):
    """
    MQTTClient provides an interface for MQTT broker.
    """

    def __init__(self, config):
        super().__init__(config, "mqtt")
        self.address = config.value_str("address")
        self.port = config.value_int("port", default=1883)
        self.keepalive = config.value_int("keepalive", default=60)
        self.reconnect_after = config.value_int("reconnect_after", default=30)
        self.loop_timeout = config.value_int("loop_timeout", default=1)
        self.client = None
        self.connected = False
        self.on_connect_ext = None
        self.on_message_ext = None
        self.log.info(f"The MQTT client configured for {self.address}")
        self.log.debug(f"The MQTT object is {self}")

    def __str__(self):
        return (
            f"name={self.name}, address={self.address}, port={self.port}, keepalive={self.keepalive}, "
            + f"reconnect_after={self.reconnect_after}, loop_timeout={self.loop_timeout}, connected={self.connected}"
        )

    def on_message(self, client, userdata, message):
        if self.on_message_ext is not None:
            try:
                self.on_message_ext(client, userdata, message)
            except Exception as e:
                self.log.error(str(e))

    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        self.client.on_message = self.on_message
        self.log.info(f"Connected to the MQTT broker at {self.address}:{self.port}")
        if self.on_connect_ext is not None:
            self.on_connect_ext(client, userdata, flags, rc)

    def on_disconnect(self, client, userdata, rc):
        self.log.info(f"Disconnected from the MQTT broker.")
        if rc != 0:
            self.log.error("The client was disconnected unexpectedly.")
        self.connected = False

    def init_client(self):
        self.client = mqtt.Client(self.name)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

    def subscribe(self, topic):
        self.log.info(f"Subscribing to events from {topic}")
        self.client.subscribe(topic)

    def wait_for_connection(self, exit_event, reconnect=False):
        if reconnect or self.client is None or not self.connected:
            if self.client is not None:
                self.client.disconnect()
                self.connected = False
            self.init_client()
            while not exit_event.is_set():
                try:
                    self.client.connect(
                        self.address, port=self.port, keepalive=self.keepalive
                    )
                    break
                except Exception as e:
                    self.log.error(
                        f"Cannot connect to the MQTT broker at {self.address}:{self.port}. {str(e)}. "
                        + f"Will attemmpt to reconnect after {self.reconnect_after} seconds."
                    )
                    exit_event.wait(self.reconnect_after)

    def worker(self, exit_event):
        self.wait_for_connection(exit_event)
        try:
            while not exit_event.is_set():
                try:
                    self.client.loop(timeout=self.loop_timeout, max_packets=1)
                    if not self.connected:
                        self.wait_for_connection(exit_event)
                except Exception as e:
                    self.log.error(f"Error occurred in the MQTT loop. {str(e)}")
                    self.wait_for_connection(exit_event, reconnect=True)
        finally:
            if self.connected:
                self.client.disconnect()


class Pattern():
    def __init__(self, pattern):
        self.match = None
        self.pattern = pattern
        self.re = re.compile(self.pattern)

    def __str__(self):
        return f"r'{self.pattern}'" if self.match is None else self.match.group(0)

    def __eq__(self, other):
        self.match = self.re.match(other)
        return self.match is not None

class Topic():
    def __init__(self, topic):
        self.name = topic["name"]
        self.disabled = topic.get("disabled", False)
        self.rules = []
        for rule_def in topic["rules"]:
            self.rules.append(Map(rule_def))

    def check_rule_data(self, read, data, scope, path=[]):
        for k,v in read.items():
            path += [k]
            if k not in data.keys():
                raise Exception(f"Missing property {k}.")
            else:
                if not isinstance(v, PythonExpression) and type(v) != type(data[k]):
                    raise Exception(f"Invalid type of property {'.'.join(path)}, found: {type(data[k]).__name__}, expected: {type(v).__name__}")
                if type(v) == dict:
                    self.check_rule_data(v, data[k], scope, path)
                else:
                    if isinstance(v, PythonExpression):
                        v = v.eval(scope)
                    if v != data[k]:
                        raise Exception(f"Invalid value of property {'.'.join(path)}, found: {data[k]}, exepcted: {v}")


class SerialMQTTBridge(Component):
    def __init__(self, config):
        super().__init__(config, "bridge")
        self.mqtt = None
        self.serial = None
        self.topics_serial2mqtt = []
        self.topics_mqtt2serial = []
        self._scope = None

        ja2mqtt_file = self.config.get_dir_path(config.root("ja2mqtt"))
        ja2mqtt = Config(ja2mqtt_file, scope=self.scope(), use_template=True)
        for topic_def in ja2mqtt("serial2mqtt"):
            self.topics_serial2mqtt.append(Topic(topic_def))
        for topic_def in ja2mqtt("mqtt2serial"):
            self.topics_mqtt2serial.append(Topic(topic_def))
        self.log.info(f"The ja2mqtt definition file is {ja2mqtt_file}")
        self.log.info(f"There are {len(self.topics_serial2mqtt)} serial2mqtt and {len(self.topics_mqtt2serial)} mqtt2serial topics.")
        self.log.debug(f"The serial2mqtt topics are: {', '.join([x.name + ('' if not x.disabled else ' (disabled)') for x in self.topics_serial2mqtt])}")
        self.log.debug(f"The mqtt2serial topics are: {', '.join([x.name + ('' if not x.disabled else ' (disabled)') for x in self.topics_mqtt2serial])}")

    def scope(self):
        if self._scope is None:
            self._scope = Map(
                topology=self.config.root("topology"),
                pattern=lambda x: Pattern(x),
                format=lambda x,**kwa: x.format(**kwa)
            )
        return self._scope

    def update_scope(self, key, value=None, remove=False):
        if self._scope is None:
            self.scope()
        if not remove:
            self._scope[key] = value
        else:
            if key in self._scope:
                del self._scope[key]

    def on_mqtt_connect(self, client, userdata, flags, rc):
        for topic in self.topics_mqtt2serial:
            self.mqtt.subscribe(topic.name)

    def on_mqtt_message(self, client, userdata, message):
        topic_name = message._topic.decode("utf-8")
        self.log.info(f"Received event from mqtt: {topic_name}")

        try:
            data = Map(json.loads(str(message.payload.decode("utf-8"))))
        except Exception as e:
            raise Exception(f"Cannot parse the event data. {str(e)}")

        self.log.debug(f"The event data is: {data}")
        for topic in self.topics_mqtt2serial:
            if not topic.disabled and topic.name == topic_name:
                for rule in topic.rules:
                    topic.check_rule_data(rule.read, data, self.scope())
                    self.log.debug("Event data conform to defined rules.")
                    self.update_scope("data", Map(data))
                    try:
                        s = deep_eval(rule.write, self._scope)
                        self.log.debug(f"Writing to serial: {s}")
                        self.serial.writeline(s)
                    finally:
                        self.update_scope("data", remove=True)

    def on_serial_data(self, data):
        self.log.debug(f"Received data from serial: {data}")
        if not self.mqtt.connected:
            self.log.warn("No events will be published. The client is not connected to the MQTT broker.")
            return

        for topic in self.topics_serial2mqtt:
            if not topic.disabled:
                for rule in topic.rules:
                    if isinstance(rule.read, PythonExpression):
                        _data = rule.read.eval(self.scope())
                    else:
                        _data = rule.read
                    if _data == data:
                        self.update_scope("data", _data)
                        try:
                            write_data = json.dumps(deep_eval(deep_merge(rule.write,{}), self._scope))
                            self.log.info(f"Publishing {write_data} to topic {topic.name}")
                            self.mqtt.client.publish(topic.name, write_data)
                        finally:
                            self.update_scope("data", remove=True)

    def set_mqtt(self, mqtt):
        self.mqtt = mqtt
        self.mqtt.on_connect_ext = self.on_mqtt_connect
        self.mqtt.on_message_ext = self.on_mqtt_message

    def set_serial(self, serial):
        self.serial = serial
        serial.on_data = self.on_serial_data
