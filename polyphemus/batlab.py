"""The plugin to use batlab as a backend build service.  This should come after 
frontends like github.

This module is available as an polyphemus plugin by the name ``polyphemus.batlab``.

BaTLaB API
=================
"""
from __future__ import print_function
import sys

from .plugins import Plugin

if sys.version_info[0] >= 3:
    basestring = str

class PolyphemusPlugin(Plugin):
    """This class provides functionality for using batlab."""

    requires = ('polyphemus.batlabrun', 'polyphemus.batlabstat')


