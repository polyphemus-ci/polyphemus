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
from .githubbase import get_pull_request_status, ensure_logged_in

class PolyphemusPlugin(Plugin):
    """This class routes the dashboard."""

    requires = ('polyphemus.batlabrun',)

    route = '/dashboard'

    request_methods = ['GET', 'POST']

    def response(self, rc):
        resp = ""
        event = banner_message = None
        if any([p.startswith('polyphemus.github') for p in rc.plugins]):
            gh = github3.GitHub()
            ensure_logged_in(gh, user=rc.github_user, credfile=rc.github_credentials)
            if request.method == 'POST':
                number = int(request.form['number'])
                pr = gh.pull_request(rc.github_owner, rc.github_repo, number)
                if rc.verbose:
                    print("Launching pull request", pr)
                event = Event(name='batlab-run', data=pr)
                banner_message = ('Launched BaTLab Job for Pull Request '
                                  '<a href="{0}">#{1}</a>')
                banner_message = banner_message.format(pr.html_url, number)
            resp = self._ghrepsonse(rc, gh, banner_message)
        else:
            resp = "No polyphemus dashboard found."
        return resp, event

    _bgcolors = {
        'success': 'rgba(149, 201, 126, 0.6)', 
        'pending': 'rgba(255, 153, 51, 0.6)', 
        'failed': 'rgba(189, 44, 0, 0.6)', 
        'error': 'rgba(51, 51, 51, 0.6)',
        }

    def _ghprinfo(self, rc, gh, r, pr):
        status = get_pull_request_status(gh, r, pr)
        if status is not None and status.description is None:
            status.description = "unhelpful message"
        bgcolor = "#ffffff" if status is None else self._bgcolors[status.state]
        return pr, status, bgcolor

    def _ghrepsonse(self, rc, gh, banner_message=None):
        r = gh.repository(rc.github_owner, rc.github_repo)
        open_prs = [self._ghprinfo(rc, gh, r, pr) for pr in r.iter_pulls(state='open')]
        closed_prs = [self._ghprinfo(rc, gh, r, pr) for pr in 
                      r.iter_pulls(state='closed', number=10)]
        return render_template("github_dashboard.html", rc=rc, open_prs=open_prs, 
                               closed_prs=closed_prs, banner_message=banner_message)
