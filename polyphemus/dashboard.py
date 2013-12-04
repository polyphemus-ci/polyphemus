"""This provides a basic issue status dashboard and a way to manually re-launch jobs.

This module is available as an polyphemus plugin by the name `polyphemus.dashboard`.

BaTLab Dashboard API
====================
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

from flask import request, render_template

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor

class PolyphemusPlugin(Plugin):
    """This class routes the dashboard."""

    requires = ('polyphemus.batlabrun',)

    route = '/dashboard'

    request_methods = ['GET', 'POST']

    def response(self, rc):
        event = None
        #if request.method == 'POST':
        if any([p.startswith('polyphemus.github') for p in rc.plugins]):
            resp = render_template("github_dashboard.html", rc=rc)
        else:
            resp = "No polyphemus dashboard found."
        return resp, event
