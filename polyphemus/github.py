"""The plug in to run on batlab.

This module is available as an polyphemus plugin by the name ``polyphemus.batlabrun``.

BaTLaB Plugin API
=================
"""
from __future__ import print_function
import os
import sys
import json
import pprint
from tempfile import NamedTemporaryFile
from warnings import warn

from flask import request

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin
from .event import Event, runfor
#from .version import report_versions

if sys.version_info[0] >= 3:
    basestring = str

class PolyphemusPlugin(Plugin):
    """This class provides functionality for getting data from github."""

    defaultrc = RunControl(
        )

    route = '/github'

    request_methods = ['GET', 'POST']

    def response(self, rc):
        print(request.method)
        payload = json.loads(request.form['payload'])
        event = Event(name='github', data=payload)
        return request.method + ": github\n", event


    @runfor('github')    
    def execute(self, rc):
        event = rc.event
        pprint.pprint(event.data)
