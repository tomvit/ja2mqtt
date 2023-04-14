from .utils import Map

from .run import command_run
from .config import command_config
from .test import command_publish

import ja2mqtt.config as ja2mqtt_config
import click
import signal
import time
import logging
import traceback


@click.group()
@click.option(
    "--no-ansi",
    "no_ansi",
    is_flag=True,
    default=False,
    help="Do not use ANSI colors",
)
@click.option(
    "--debug",
    "debug",
    is_flag=True,
    default=False,
    help="Print debug information",
)
def ja2mqtt(no_ansi, debug):
    if no_ansi:
        ja2mqtt_config.ANSI_COLORS = False
    if debug:
        ja2mqtt_config.DEBUG = True

def signal_quit(signal, frame):
    """
    Function called when process ends when any signal is received. The function
    sets the `exit_event` so that all worker threads using the event can gracefully end.
    """
    ja2mqtt_config.exit_event.set()

ja2mqtt.add_command(command_run)
ja2mqtt.add_command(command_config)
ja2mqtt.add_command(command_publish)

# register `signal_quit` function for all signals.
for sig in ("TERM", "HUP", "INT"):
    signal.signal(getattr(signal, "SIG" + sig), signal_quit)

try:
    log = logging.getLogger("main")
    ja2mqtt(prog_name="ja2mqtt")
except Exception as e:
    log.error(f"ERROR: {str(e)}")
    if ja2mqtt_config.DEBUG:
        print("---")
        traceback.print_exc()
        print("---")
