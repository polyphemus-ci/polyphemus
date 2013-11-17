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

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor

class PolyphemusPlugin(Plugin):
    """This class routes batlab status updates."""

    requires = ('polyphemus.batlabbase',)

    route = '/batlabstatus'

    request_methods = ['GET', 'POST']

    _rm_job_stats = frozenset(['success', 'failure', 'error'])

    def response(self, rc):
        if 'status' not in request.form:
            return "\n", None
        data = json.loads(request.form['status'])
        if 'status' not in data:
            return "\n", None
        jobs = PersistentCache(cachefile=rc.batlab_jobs_cache)
        job = (rc.github_owner, rc.github_repo, data['number'])
        if job in jobs:
            if 'target_url' not in data or not data['target_url'].startswith('http'):
                data['target_url'] = jobs[job]['report_url']
            if data['status'] in self._rm_job_stats:
                del jobs[job]
        event = Event(name='batlab-status', data=data)
        return request.method + ": batlab\n", event
