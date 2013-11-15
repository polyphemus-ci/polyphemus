"""The plugin to recieve status updates from batlab and re-dispatch them.

This module is available as an polyphemus plugin by the name `polyphemus.batlabstat`.

BaTLab Status API
=================
"""
from __future__ import print_function
import os
import io
import sys
import pprint
from warnings import warn

if sys.version_info[0] >= 3:
    basestring = str

try:
    import simplejson as json
except ImportError:
    import json

from flask import request

from .utils import RunControl, NotSpecified
from .plugins import Plugin
from .event import Event, runfor

class PolyphemusPlugin(Plugin):
    """This class routes batlab status updates."""

    requires = ('polyphemus.batlabbase',)

    route = '/batlabstatus'

    request_methods = ['GET', 'POST']

    def response(self, rc):
        data = json.loads(request.data)
        if 'status' not in rawdata:
            return "\n", None
        event = Event(name='batlab-status', data=data)
        return request.method + ": batlab\n", event
