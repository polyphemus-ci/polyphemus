"""The basic functionality for SWC website plugins

This module is available as an polyphemus plugin by the name `polyphemus.swcbase`.

Basic SWC API
=============
"""
from __future__ import print_function
import os
import sys
from warnings import warn

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin

if sys.version_info[0] >= 3:
    basestring = str

HTML_EXTS = set(['.html', '.htm'])

KNOWN_EXTS = set(['.html', '.htm', '.ipynb'])

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
