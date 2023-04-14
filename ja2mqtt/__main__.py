from .utils import Map

from .run import command_run
from .config import command_config

import ja2mqtt.config as ja2mqtt_config
import click


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


ja2mqtt.add_command(command_run)
ja2mqtt.add_command(command_config)

ja2mqtt(prog_name="ja2mqtt")
