# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json
import logging
import re
import threading
import time
from queue import Queue

import paho.mqtt.client as mqtt
import serial as py_serial

from ja2mqtt.config import Config
from ja2mqtt.utils import Map, PythonExpression, deep_eval, deep_merge, merge_dicts

from . import Component
from .simulator import Simulator


class MQTT(Component):
    """
    MQTTClient provides an interface for MQTT broker.
    """

    def __init__(self, name, config):
        super().__init__(config, "mqtt")
        self.client_name = name
        self.address = self.config.value_str("address")
        self.port = self.config.value_int("port", default=1883)
        self.keepalive = self.config.value_int("keepalive", default=60)
        self.reconnect_after = self.config.value_int("reconnect_after", default=30)
        self.loop_timeout = self.config.value_int("loop_timeout", default=1)
        self.username = self.config.value_str("username", default=None)
        self.password = self.config.value_str("password", default=None)
        self.protocol = {
            "MQTTv311": mqtt.MQTTv311,
            "MQTTv31": mqtt.MQTTv31,
            "MQTTv5": mqtt.MQTTv5,
            "default": None,
        }[self.config.value_str("protocol", default="MQTTv311")]
        self.transport = self.config.value_str("transport", default="tcp")
        self.clean_session = self.config.value_str("clean_session", default=None)
        self.client = None
        self.connected = False
        self.on_connect_ext = None
        self.on_message_ext = None
        self.on_error_ext = None
        self.log.info(f"The MQTT client configured for {self.address}.")
        self.log.debug(f"The MQTT object is {self}.")

    def __str__(self):
        return (
            f"{self.__class__}: name={self.name}, address={self.address}, port={self.port}, keepalive={self.keepalive}, "
            + f"reconnect_after={self.reconnect_after}, loop_timeout={self.loop_timeout}, connected={self.connected}"
        )

    def on_error(self, exception):
        self.log.error(str(exception))
        if self.on_error_ext is not None:
            self.on_error_ext(exception)

    def on_message(self, client, userdata, message):
        topic_name = message._topic.decode("utf-8")
        payload = str(message.payload.decode("utf-8"))
        self.log.info(f"--> recv: {topic_name}, payload={payload}")
        if self.on_message_ext is not None:
            try:
                self.on_message_ext(topic_name, payload)
            except Exception as e:
                self.on_error(e)

    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        self.client.on_message = self.on_message
        self.log.info(f"Connected to the MQTT broker at {self.address}:{self.port}")
        if self.on_connect_ext is not None:
            try:
                self.on_connect_ext(client, userdata, flags, rc)
            except Exception as e:
                self.on_error(e)

    def on_disconnect(self, client, userdata, rc):
        try:
            self.log.info(f"Disconnected from the MQTT broker.")
            self.connected = False
            if rc != 0:
                raise Exception("The client was disconnected unexpectedly.")
        except Exception as e:
            self.on_error(e)

    def init_client(self):
        self.client = mqtt.Client(
            self.client_name,
            clean_session=self.clean_session,
            protocol=self.protocol,
            transport=self.transport,
        )
        if self.username is not None:
            self.log.debug(
                f"Using '{self.username}/*******' to authenticate with the MQTT broker."
            )
            if self.password is None:
                self.log.warning("The password was not specified!")
            self.client.username_pw_set(username=self.username, password=self.password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

    def subscribe(self, topic):
        self.log.info(f"Subscribing to {topic}")
        self.client.subscribe(topic)

    def publish(self, topic, data):
        self.log.info(f"<-- send: {topic}, data={data}")
        self.client.publish(topic, data)

    def __wait_for_connection(self, exit_event, reconnect=False):
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
                    self.on_error(
                        Exception(
                            f"Cannot connect to the MQTT broker at {self.address}:{self.port}. {str(e)}. "
                            + f"Will attemmpt to reconnect after {self.reconnect_after} seconds."
                        )
                    )
                    exit_event.wait(self.reconnect_after)

    def wait_is_connected(self, exit_event, timeout=0):
        start_time = time.time()
        while (
            not exit_event.is_set()
            and not self.connected
            and (timeout == 0 or time.time() - start_time <= timeout)
        ):
            exit_event.wait(0.2)
        return self.connected

    def worker(self, exit_event):
        self.__wait_for_connection(exit_event)
        try:
            while not exit_event.is_set():
                try:
                    self.client.loop(timeout=self.loop_timeout, max_packets=1)
                    if not self.connected:
                        raise Exception("Not connected to MQTT broker.")
                except Exception as e:
                    self.on_error(
                        Exception(
                            f"Error occurred in the MQTT loop. {str(e)}"
                            + f"Will attemmpt to reconnect after {self.reconnect_after} seconds."
                        )
                    )
                    exit_event.wait(self.reconnect_after)
                    self.__wait_for_connection(exit_event, reconnect=True)
        finally:
            if self.connected:
                self.client.disconnect()
            self.log.info("MQTT worker ended.")
