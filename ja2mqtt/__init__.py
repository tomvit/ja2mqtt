# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import pkg_resources
import importlib.metadata

__version__ = "2.0.0"

def get_version():
    git_commit_id = None
    try:
        pkg_info = pkg_resources.get_distribution('ja2mqtt')
        version = pkg_info.version

        entry_points = importlib.metadata.entry_points()
        metadata = entry_points.get('distutils.metadata')
        if metadata:
            git_commit_id = metadata[0].value

    except Exception as e:
        print(str(e))
        version = __version__
    return version, git_commit_id

def get_version_string():
    version, commit = get_version()
    if commit is not None:
        return f"{version}-{commit[:10]}"
    else:
        return version
