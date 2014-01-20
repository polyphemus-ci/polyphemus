"""The basic functionality for BaTLab.

This module is available as an polyphemus plugin by the name `polyphemus.batlabbase`.

Basic BaTLaB API
=================
"""
from __future__ import print_function
import os
import sys
from tempfile import NamedTemporaryFile
import subprocess
from warnings import warn
from getpass import getuser, getpass

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin
from .base import ssh_pub_key

if sys.version_info[0] >= 3:
    basestring = str

class PolyphemusPlugin(Plugin):
    """This class provides basic Software Carpentry functionality."""

    requires = ('polyphemus.base',)

    defaultrc = RunControl()

    rcdocs = {}

    def update_argparser(self, parser):
        #parser.add_argument('--batlab-user', dest='batlab_user',
        #                    help=self.rcdocs["batlab_user"])
        pass

    def setup(self, rc):
        pass
