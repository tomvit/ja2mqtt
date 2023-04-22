# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import json
import logging
import re
import threading
import time
from queue import Empty, Queue

import paho.mqtt.client as mqtt

from ja2mqtt.config import Config
from ja2mqtt.utils import Map, PythonExpression, deep_eval, deep_merge, merge_dicts

from . import Component
from .serial import SerialJA121TException, decode_prfstate


class Pattern:
    """
    Pattern class is used in the scope to evaluate that a data string matches the pattern
    defined in the ja2mqtt rule. It is possible to use the equal operator to compare the data string
    with the pattern object and then use the matcher to retrieve captured groups
    for the `wrtie` condition of the rule.
    """

    def __init__(self, pattern):
        self.match = None
        self.pattern = pattern
        self.re = re.compile(self.pattern)

    def __str__(self):
        return f"r'{self.pattern}'" if self.match is None else self.match.group(0)

    def __eq__(self, other):
        self.match = self.re.match(other)
        return self.match is not None


class PrfStateChange:
    def __init__(self, pos, current_prfstate):
        self.pos = pos
        self.current_prfstate = current_prfstate
        self.state = None

    def __str__(self):
        return f"position={self.pos}, state={self.state}"

    def __eq__(self, other):
        if other.startswith("PRFSTATE"):
            d = decode_prfstate(other.split(" ")[1])
            self.state = d[self.pos]
            return (
                self.current_prfstate is None
                or d[self.pos] != self.current_prfstate[self.pos]
            )
        else:
            return False


class Topic:
    def __init__(self, topic):
        self.name = topic["name"]
        self.disabled = topic.get("disabled", False)
        self.rules = []
        for rule_def in topic["rules"]:
            self.rules.append(Map(rule_def))

    def check_rule_data(self, read, data, scope, path=None):
        if path is None:
            path = []
        try:
            for k, v in read.items():
                path += [k]
                if k not in data.keys():
                    raise Exception(f"Missing property {k}.")
                else:
                    if not isinstance(v, PythonExpression) and type(v) != type(data[k]):
                        raise Exception(
                            f"Invalid type of property {'.'.join(path)}, "
                            + f"found: {type(data[k]).__name__}, expected: {type(v).__name__}"
                        )
                    if type(v) == dict:
                        self.check_rule_data(v, data[k], scope, path)
                    else:
                        if isinstance(v, PythonExpression):
                            v = v.eval(scope)
                        if v != data[k]:
                            raise Exception(
                                f"Invalid value of property {'.'.join(path)}, "
                                + f"found: {data[k]}, exepcted: {v}"
                            )
        except Exception as e:
            raise Exception(f"Topic data validation failed. {str(e)}")


class SerialMQTTBridge(Component):
    def __init__(self, config):
        def _list(topics):
            return ", ".join(
                [x.name + ("" if not x.disabled else " (disabled)") for x in topics]
            )

        super().__init__(config, "bridge")
        self.mqtt = None
        self.serial = None
        self.topics_serial2mqtt = []
        self.topics_mqtt2serial = []
        self._scope = None
        self.request_queue = Queue()

        ja2mqtt_file = self.config.get_dir_path(config.root("ja2mqtt"))
        ja2mqtt = Config(ja2mqtt_file, scope=self.scope(), use_template=True)
        for topic_def in ja2mqtt("serial2mqtt"):
            self.topics_serial2mqtt.append(Topic(topic_def))
        for topic_def in ja2mqtt("mqtt2serial"):
            self.topics_mqtt2serial.append(Topic(topic_def))
        self.correlation_id = ja2mqtt("system.correlation_id", None)
        self.correlation_timeout = ja2mqtt("system.correlation_timeout", 0)
        self.topic_sys_error = ja2mqtt("system.topic_sys_error", None)
        self.prfstate_bits = ja2mqtt("system.prfstate_bits", 128)
        self.request = None
        self.prfstate = [decode_prfstate("".zfill(self.prfstate_bits))]

        self.log.info(f"The ja2mqtt definition file is {ja2mqtt_file}")
        self.log.info(
            f"There are {len(self.topics_serial2mqtt)} serial2mqtt and "
            + f"{len(self.topics_mqtt2serial)} mqtt2serial topics."
        )
        self.log.debug(f"The serial2mqtt topics are: {_list(self.topics_serial2mqtt)}")
        self.log.debug(f"The mqtt2serial topics are: {_list(self.topics_mqtt2serial)}")

    def update_correlation(self, data):
        if self.request_queue.qsize() > 0:
            self.request = self.request_queue.get()
        if self.request is not None:
            if (
                time.time() - self.request.created_time < self.correlation_timeout
                and self.request.ttl > 0
            ):
                if self.request.cor_id is not None:
                    data[self.correlation_id] = self.request.cor_id
                self.request.ttl -= 1
            else:
                self.log.debug(
                    "Discarding the request for correlation. The correlation timeout "
                    + "or TTL expired."
                )
                self.request = None
        return data

    def scope(self):
        def _write_prf_state(reset=False):
            if reset:
                self.log.debug("Reseting prfstate object to None.")
                self.prfstate = []
            return "PRFSTATE"

        if self._scope is None:
            self._scope = Map(
                topology=self.config.root("topology"),
                pattern=lambda x: Pattern(x),
                format=lambda x, **kwa: x.format(**kwa),
                prf_state_change=lambda pos: PrfStateChange(
                    str(pos), self.prfstate[-2] if len(self.prfstate) > 1 else None
                ),
                write_prf_state=_write_prf_state,
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

    def update_prfstate(self, data_str):
        try:
            if data_str.startswith("PRFSTATE"):
                self.prfstate.append(decode_prfstate(data_str.split(" ")[1]))
                if len(self.prfstate) > 1:
                    self.prfstate = self.prfstate[-2:]
                self.log.debug(f"prfstate_decoded={self.prfstate[-1]}")
        except SerialJA121TException as e:
            self.log.error({str(e)})

    def on_mqtt_connect(self, client, userdata, flags, rc):
        for topic in self.topics_mqtt2serial:
            self.mqtt.subscribe(topic.name)

    def on_mqtt_message(self, topic_name, payload):
        if not self.serial.is_ready():
            self.log.warn(
                "No messages will be processed. The serial interface is not available."
            )
            return
        try:
            data = Map(json.loads(payload))
        except Exception as e:
            raise Exception(f"Cannot parse the event data. {str(e)}")

        self.log.debug(f"The event data parsed as JSON object: {data}")
        for topic in self.topics_mqtt2serial:
            if topic.name == topic_name:
                if topic.disabled:
                    continue
                for rule in topic.rules:
                    if rule.read is not None:
                        topic.check_rule_data(rule.read, data, self.scope())
                        self.log.debug(
                            "The event data is valid according to the defined rules."
                        )
                    _data = Map(data)
                    self.update_scope("data", _data)
                    try:
                        s = deep_eval(rule.write, self._scope)
                        self.request_queue.put(
                            Map(
                                cor_id=_data.get(self.correlation_id),
                                created_time=time.time(),
                                ttl=rule.get("request_ttl", 1),
                            )
                        )
                        self.serial.writeline(s)
                    finally:
                        self.update_scope("data", remove=True)

    def on_serial_data(self, data):
        if not self.mqtt.connected:
            self.log.warn(
                "No events will be published. The client is not connected to the MQTT broker."
            )
            return

        self.update_prfstate(data)
        _rule = None
        current_time = time.time()
        for topic in self.topics_serial2mqtt:
            for rule in topic.rules:
                if isinstance(rule.read, PythonExpression):
                    _data = rule.read.eval(self.scope())
                else:
                    _data = rule.read
                if _data == data:
                    _rule = rule
                    if not topic.disabled:
                        self.update_scope("data", _data)
                        try:
                            d0 = self.update_correlation(Map())
                            if not rule.require_request or self.request is not None:
                                if rule.no_correlation:
                                    d0 = {}
                                d1 = deep_merge(rule.write, d0)
                                d2 = deep_eval(d1, self._scope)
                                write_data = json.dumps(d2)
                                self.mqtt.publish(topic.name, write_data)
                                if not _rule.process_next_rule:
                                    break
                        finally:
                            self.update_scope("data", remove=True)
            if _rule is not None and not _rule.process_next_rule:
                break

        if _rule is None:
            self.log.debug(f"No rule found for the data: {data}")

    def set_mqtt(self, mqtt):
        self.mqtt = mqtt
        self.mqtt.on_connect_ext = self.on_mqtt_connect
        self.mqtt.on_message_ext = self.on_mqtt_message

    def set_serial(self, serial):
        self.serial = serial

    def worker(self, exit_event):
        self.log.info("Running bridge worker, reading events from the serial buffer.")
        try:
            if self.serial is None:
                raise Exception("Serial object has not been set!")
            while not exit_event.is_set():
                try:
                    data = self.serial.buffer.get(timeout=1)
                    self.on_serial_data(data)
                except Empty as e:
                    pass
        finally:
            self.log.info("Bridge worker ended.")
