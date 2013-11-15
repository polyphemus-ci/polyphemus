"""The plugin to recieve posts from batlab and update the status of the pull request.

This module is available as an polyphemus plugin by the name ``polyphemus.githubstat``.

GitHub Status API
=================
"""
from __future__ import print_function
import os
import io
import sys
from warnings import warn

if sys.version_info[0] >= 3:
    basestring = str

try:
    import simplejson as json
except ImportError:
    import json

from github3 import GitHub
import github3.events

from .utils import RunControl, NotSpecified, writenewonly
from .plugins import Plugin
from .event import Event, runfor
from .githubbase import set_pull_request_status

class PolyphemusPlugin(Plugin):
    """This class provides functionality for updating pull request statuses on 
    github.
    """

    requires = ('polyphemus.githubbase',)

    _status_descs = {
        'success': 'Great Success!', 
        'pending': 'Patience, discipline.',
        'failure': 'It turns out failure *was* an option.',
        'error': 'Error: does not compute.',
        }

    @runfor('batlab-status')
    def execute(self, rc):
        """The githubstat plugin is only executed for 'batlab-status' events and 
        requires that the event data be a dictionary with 'status' and 'number' as
        keys.  It optionally may also include 'target_url' and 'description' keys.
        """
        data = rc.event.data
        pr = (rc.github_owner, rc.github_repo, data['number'])
        set_pull_request_status(pr, data['status'], 
            target_url=data.get('target_url', ""), 
            description=data.get('description', self._status_descs[data['status']]), 
            user=rc.github_user, credfile=rc.github_credentials)
