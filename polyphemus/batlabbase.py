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

if sys.version_info[0] >= 3:
    basestring = str

BATLAB_SUBMIT_URL = 'submit-1.batlab.org'

class PolyphemusPlugin(Plugin):
    """This class provides basic BaTLab functionality."""

    defaultrc = RunControl(
        'batlab_user': NotSpecified,
        )

    rcdocs = {
        'batlab_user': ("The BaTLab user name to login with.  Must have rights "
                        "on the submit node."),
        }

    def update_argparser(self, parser):
        parser.add_argument('--batlab-user', dest='batlab_user',
                            help=self.rcdocs["batlab_user"])

    def setup(self, rc):
        if rc.batlab_user is NotSpecified:
            user = getuser()
            print("batlab username not specified, found {0!r}".format(user))
            rc.batlab_user = user
