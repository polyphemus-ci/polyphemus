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

    defaultrc = RunControl(swc_cache='swc.cache')

    rcdocs = {'swc_cache': 'Filename for software carpentry cache.'}

    def update_argparser(self, parser):
        parser.add_argument('--swc-cache', dest='swc_cache',
                            help=self.rcdocs["swc_cache"])

    def setup(self, rc):
        pass
