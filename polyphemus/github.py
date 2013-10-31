"""The plug in to run on batlab.

This module is available as an polyphemus plugin by the name ``polyphemus.batlabrun``.

BaTLaB Plugin API
=================
"""
from __future__ import print_function
import os
import sys
import pprint
from tempfile import NamedTemporaryFile
from warnings import warn

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin
#from .version import report_versions

if sys.version_info[0] >= 3:
    basestring = str

fetch_template = \
"""method = git
git_repo = {repo}
git_path = cyclus;cd cyclus;git checkout {branch}
"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for getting data from github."""

    defaultrc = RunControl(
        )

    def execute(self, rc):
        event = rc.event
        if event.name != 'github':
            return
        pprint.pprint(event.data.payload)
