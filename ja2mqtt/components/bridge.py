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
from ja2mqtt.utils import (
    Map,
    PythonExpression,
    deep_eval,
    deep_merge,
    merge_dicts,
    randomString,
)

from . import Component
from .serial import SerialJA121TException, decode_prfstate

PRFSTATE_RE = re.compile("PRFSTATE ([0-9A-F]+)")


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
    """
    PrfStateChange evaluates a state change in a peripheral at position `pos`. It uses
    the current state object that represents decoded peripheral states (a result of
    `decode_prfstate`) and compares a new decoded state with the curent state at
    a position `pos`. If the state changes, the `__eq__` method returns True otherwise
    it returns False. After the evaluation of equality, the property `state` contains
    the current state of the peripheral and property `updated` contains the updated
    time of the peripheral.
    """

    def __init__(self, pos, current_state):
        self.pos = pos
        self.current_state = current_state
        self.state = None
        self.updated = None

    def __str__(self):
        """
        String representation of the oject.
        """
        return f"pos={self.pos}, state={self.state}"

    def decode(self, line):
        """
        Decode line to dict where keys are codes and values are states.
        """
        if line.startswith("PRFSTATE"):
            d = decode_prfstate(line.split(" ")[1])
            return True, d
        else:
            return False, None

    def __eq__(self, other):
        res, d = self.decode(other)
        if res:
            if self.state != d[self.pos]:
                self.updated = time.time()
            self.state = d[self.pos]
            res = (
                self.current_state is None
                or d[self.pos] != self.current_state[self.pos]
            )
        return res


class SectionState:
    def __init__(self, pattern, section_group=1, state_group=2):
        self.re = re.compile(pattern)
        self.section_group = section_group
        self.state_group = state_group
        self.state = None
        self.match = None
        self.updated = None

    def __eq__(self, other):
        self.match = self.re.match(other)
        if self.match:
            section = self.match.group(self.section_group)
            state = self.match.group(self.state_group)
            if self.state != state:
                self.updated = time.time()
                self.state = state
            return True
        else:
            return False


class PrfState:
    def __init__(self, pos):
        self.state = None
        self.pos = str(pos)
        self.report_on_next = False

    def __eq__(self, other):
        res = False
        if other.startswith("PRFSTATE"):
            d = decode_prfstate(other.split(" ")[1])
            if self.state != d[self.pos]:
                self.state = d[self.pos]
                self.updated = time.time()
                res = True
            if self.report_on_next:
                self.report_on_next = False
                res = True
        return res


class Topic:
    def __init__(self, prefix, topic):
        if topic["name"].startswith(prefix):
            self.name = topic["name"]
        else:
            sep = "/"
            if prefix[-1] == "/" or topic["name"][0] == "/":
                sep = ""
            self.name = prefix + sep + topic["name"]
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

    @classmethod
    def list(cls, topics):
        return ", ".join(
            [x.name + ("" if not x.disabled else " (disabled)") for x in topics]
        )


class JA2MQTTConfig:
    def __init__(self, config):
        self._scope = None
        self.config = config
        self.topics_serial2mqtt = []
        self.topics_mqtt2serial = []
        self.ja2mqtt_file = self.config.get_dir_path(config.root("ja2mqtt"))
        self.ja2mqtt = Config(
            self.ja2mqtt_file,
            scope=self.scope(),
            use_template=True,
            schema="ja2mqtt-schema.yaml",
        )

        # system properties
        self.topic_prefix = self.ja2mqtt("system.topic_prefix", "ja2mqtt")
        self.correlation_id = self.ja2mqtt("system.correlation_id", None)
        self.correlation_timeout = self.ja2mqtt("system.correlation_timeout", 0)
        self.topic_sys_error = self.ja2mqtt("system.topic_sys_error", None)
        self.prfstate_bits = self.ja2mqtt("system.prfstate_bits", 128)

        # topics
        for topic_def in self.ja2mqtt("serial2mqtt"):
            self.topics_serial2mqtt.append(Topic(self.topic_prefix, topic_def))
        for topic_def in self.ja2mqtt("mqtt2serial"):
            self.topics_mqtt2serial.append(Topic(self.topic_prefix, topic_def))

    def scope(self):
        section_states = {}

        def _section_state(pattern, g1, g2):
            if pattern not in section_states:
                section_states[pattern] = SectionState(pattern, g1, g2)
            return section_states[pattern]

        prf_states = {}

        def _prf_state(pos):
            if pos not in prf_states:
                prf_states[pos] = PrfState(pos)
            return prf_states[pos]

        def _write_prf_state():
            for k, v in prf_states.items():
                v.report_on_next = True
            return "PRFSTATE"

        if self._scope is None:
            self._scope = Map(
                topology=self.config.root("topology"),
                pattern=lambda x: Pattern(x),
                format=lambda x, **kwa: x.format(**kwa),
                prf_state=lambda pos: _prf_state(pos),
                section_state=lambda pattern, g1, g2: _section_state(pattern, g1, g2),
                write_prf_state=_write_prf_state,
            )
        return self._scope

    def corr_id(self):
        corrid_field = self.ja2mqtt("system.correlation_id", None)
        corr_id = randomString(12, letters="abcdef0123456789")
        return corrid_field, corr_id if corrid_field is not None else None

    def topic_exists(self, name):
        return name in [x.name for x in self.topics_mqtt2serial]


class SerialMQTTBridge(Component, JA2MQTTConfig):
    def __init__(self, config):
        Component.__init__(self, config, "bridge")
        JA2MQTTConfig.__init__(self, config)
        self.mqtt = None
        self.serial = None
        self._scope = None
        self.request_queue = Queue()
        self.request = None

        self.log.info(f"The ja2mqtt definition file is {self.ja2mqtt_file}")
        self.log.info(
            f"There are {len(self.topics_serial2mqtt)} serial2mqtt and "
            + f"{len(self.topics_mqtt2serial)} mqtt2serial topics."
        )
        self.log.debug(
            f"The serial2mqtt topics are: {Topic.list(self.topics_serial2mqtt)}"
        )
        self.log.debug(
            f"The mqtt2serial topics are: {Topic.list(self.topics_mqtt2serial)}"
        )

        # states of perihperals
        self.prfstate = [decode_prfstate("".zfill(self.prfstate_bits))]

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
            m = PRFSTATE_RE.match(data_str)
            if m:
                self.prfstate.append(decode_prfstate(m.group(1)))
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
