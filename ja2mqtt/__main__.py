import logging
import signal
import sys
import time
import traceback

import click

import ja2mqtt.config as ja2mqtt_config

from .commands import ja2mqtt
from .utils import Map


def signal_quit(signal, frame):
    """
    Function called when process ends when any signal is received. The function
    sets the `exit_event` so that all worker threads using the event can gracefully end.
    """
    ja2mqtt_config.exit_event.set()


# register `signal_quit` function for all signals.
for sig in ("TERM", "HUP", "INT"):
    signal.signal(getattr(signal, "SIG" + sig), signal_quit)

try:
    ja2mqtt(prog_name="ja2mqtt")
except Exception as e:
    sys.stderr.write(f"ERROR: {str(e)}\n")
    if ja2mqtt_config.DEBUG:
        print("---")
        traceback.print_exc()
        print("---")
