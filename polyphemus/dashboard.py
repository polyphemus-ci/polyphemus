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

import github3

from flask import request, render_template

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor
from .githubbase import get_pull_request_status

class PolyphemusPlugin(Plugin):
    """This class routes the dashboard."""

    requires = ('polyphemus.batlabrun',)

    route = '/dashboard'

    request_methods = ['GET', 'POST']

    def response(self, rc):
        event = None
        #if request.method == 'POST':
        if any([p.startswith('polyphemus.github') for p in rc.plugins]):
            resp = self._ghrepsonse(rc)
        else:
            resp = "No polyphemus dashboard found."
        return resp, event

    def _ghrepsonse(self, rc):
        r = github3.repository(rc.github_owner, rc.github_repo)
        open_prs = []
        closed_prs = []
        for pr in r.iter_pulls():
            status = get_pull_request_status(r, pr)
            if status.description is None:
                status.description = "unhelpful message"
            if pr.state == 'open':
                open_prs.append((pr, status))
            else:
                closed_prs.append((pr, status))
        return render_template("github_dashboard.html", rc=rc, open_prs=open_prs, 
                               closed_prs=closed_prs)
