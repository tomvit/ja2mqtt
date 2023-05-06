#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import codecs
import os
import re
import sys
import argparse
import glob

from setuptools import find_packages
from setuptools import setup

# read file content
def read(*parts):
    path = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(path, encoding='utf-8') as fobj:
        return fobj.read()

# Read the version number from __init__.py
here = os.path.abspath(os.path.dirname(__file__))
version_file = os.path.join(here, 'ja2mqtt', '__init__.py')
exec(open(version_file).read())

# setup main
# required modules
install_requires = [
    'click>=8.0.4',
    'Jinja2>=3.0.3',
    'paho-mqtt>=1.6.1',
    'pyserial>=3.5',
    'PyYAML>=6.0',
    'jsonschema>=4.0.0'
]

setup(
    name='ja2mqtt',
    version=__version__,
    description='Jablotron MQTT bridge',
    long_description=read('README-pypi.text'),
    py_modules=['ja2mqtt'],
    author='Tomas Vitvar',
    author_email='tomas@vitvar.com',
    packages=find_packages(exclude=['tests.*', 'tests']),
    include_package_data=True,
    install_requires=install_requires,
    python_requires='>=3.6.0',
    #scripts=['bin/ja2mqtt'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points='''
        [console_scripts]
        ja2mqtt=ja2mqtt.commands.ja2mqtt:ja2mqtt
    ''',
)
