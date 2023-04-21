# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import, unicode_literals

import signal
import sys
import traceback

import click

import ja2mqtt.config as ja2mqtt_config
from ja2mqtt import __version__
from ja2mqtt.commands.config import command_config
from ja2mqtt.commands.run import command_run
from ja2mqtt.commands.test import command_publish
from ja2mqtt.utils import bcolors, format_str_color


class CoreCommand(click.core.Group):
    def invoke(self, ctx):
        ja2mqtt_config.ANSI_COLORS = not ctx.params.get("no-ansi", False)
        ja2mqtt_config.DEBUG = ctx.params.get("debug", False)
        try:
            for sig in ("TERM", "HUP", "INT"):
                signal.signal(
                    getattr(signal, "SIG" + sig),
                    lambda x, y: ja2mqtt_config.exit_event.set(),
                )
            click.core.Group.invoke(self, ctx)
        except click.exceptions.Exit as e:
            sys.exit(int(str(e)))
        except click.core.ClickException as e:
            raise e
        except Exception as e:
            sys.stderr.write(
                format_str_color(
                    f"ERROR: {str(e)}\n", bcolors.ERROR, not ja2mqtt_config.ANSI_COLORS
                )
            )
            if ja2mqtt_config.DEBUG:
                print("---")
                traceback.print_exc()
                print("---")

            sys.exit(1)


@click.group(cls=CoreCommand)
@click.option("--no-ansi", "no_ansi", is_flag=True, default=False, help="No colors.")
@click.option("-d", "--debug", "debug", is_flag=True, default=False, help="Be verbose.")
@click.version_option(version=__version__)
def ja2mqtt(debug, no_ansi):
    pass


ja2mqtt.add_command(command_run)
ja2mqtt.add_command(command_config)
ja2mqtt.add_command(command_publish)
