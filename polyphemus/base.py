"""The base plugin for polyphemus.

This module is available as an polyphemus plugin by the name ``polyphemus.base``.

Base Plugin API
===============
"""
from __future__ import print_function
import os
import sys
from warnings import warn

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent
from .plugins import Plugin
from .version import report_versions

if sys.version_info[0] >= 3:
    basestring = str

class PolyphemusPlugin(Plugin):
    """This class provides base functionality for polyhemus itself."""

    defaultrc = RunControl(
        rc=DEFAULT_RC_FILE,
        plugins=DEFAULT_PLUGINS,
        debug=False,
        debug_filename='debug.txt',
        verbose=False,
        version=False,
        bash_completion=True,
        )

    rcdocs = {
        'rc': "Path to run control file",
        'plugins': "Plugins to include",
        'debug': 'run in debugging mode', 
        'debug_filename': 'the path to the debug file', 
        'verbose': "Print more output.",
        'version': "Print version information.",
        'bash_completion': ("Flag for enabling / disabling BASH completion. "
                            "This is only relevant when using argcomplete."),
        }

    def update_argparser(self, parser):
        parser.add_argument('--rc', help=self.rcdocs['rc'])
        parser.add_argument('--plugins', nargs="+", help=self.rcdocs["plugins"])
        parser.add_argument('--debug', action='store_true', 
                            help=self.rcdocs["debug"])
        parser.add_argument('--debug-filename', dest='debug_filename', 
                            help=self.rcdocs["debug_filename"])
        parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                            help=self.rcdocs["verbose"])
        parser.add_argument('--version', action='store_true', dest='version',
                            help=self.rcdocs["version"])

    def setup(self, rc):
        if rc.version:
            print(report_versions())
            sys.exit()

    def report_debug(self, rc):
        msg = 'Version Information:\n\n{0}\n\n'
        msg += nyansep + "\n\n"
        return msg

