# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

import logging
import threading


class Component:
    """
    Base class for all components.
    """

    def __init__(self, config, name):
        self.log = logging.getLogger(name)
        self.config = config
        self.name = name
        self.thread = None

    def worker(self, exit_event):
        """
        The worker method that is executed in a separate thread.
        """
        pass

    def join(self):
        """
        Wait for the thread to finish.
        """
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()

    def start(self, exit_event):
        """
        Start the component thread.
        """
        self.thread = threading.Thread(
            target=self.worker, args=(exit_event,), daemon=True
        )
        self.thread.start()


# pylint: disable=wrong-import-position
from .bridge import SerialMQTTBridge, JA2MQTTConfig
from .mqtt import MQTT
from .serial import Serial
from .simulator import Simulator
