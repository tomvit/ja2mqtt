# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import logging
import threading


class Component:
    def __init__(self, config, name):
        self.log = logging.getLogger(name)
        self.config = config
        self.name = name
        self.thread = None

    def worker(self, exit_event):
        pass

    def join(self):
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()

    def start(self, exit_event):
        self.thread = threading.Thread(
            target=self.worker, args=(exit_event,), daemon=True
        )
        self.thread.start()


from .bridge import SerialMQTTBridge
from .mqtt import MQTT
from .serial import Serial
from .simulator import Simulator
