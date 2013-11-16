"""The plugin to recieve posts from github and dispatch them to certain events.

This module is available as an polyphemus plugin by the name ``polyphemus.githubhook``.

GitHub Hook API
=================
"""
from __future__ import print_function
import os
import io
import sys
import pprint
import socket
from warnings import warn
from getpass import getuser, getpass
from tempfile import NamedTemporaryFile

if sys.version_info[0] >= 3:
    basestring = str
    from urllib.request import urlopen
else:
    from urllib2 import urlopen

try:
    import simplejson as json
except ImportError:
    import json

from github3 import GitHub
import github3.events
from flask import request

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin
from .event import Event, runfor
from .githubbase import ensure_logged_in, set_pull_request_status

def verify_hook(owner, repo, url, events, user=None, credfile='gh.cred'):
    """Ensures that the github WebURL API hook has been set up properly.

    Parameters
    ----------
    owner : str
        The GitHub repository owner.
    repo : str
        The GitHub repository name.
    url : str
        The url of the hook.
    events : list of str
        The list GitHub events that this hook should trigger on.  GitHub 
        defaults this to ['pull'] but ['pull_request'] is a more reasonable value.
    user : str, None, or NotSpecified, optional
        The username to log into github with.
    credfile : str, optional
        The github credentials file name.

    """
    gh = GitHub()
    ensure_logged_in(gh, user=user, credfile=credfile)
    r = gh.repository(owner, repo)
    for hook in r.iter_hooks():
        if hook.name != 'web':
            continue
        elif hook.config['url'] == url:
            break
    else:
        hook = r.create_hook(name='web', config={"url": url, "content_type": "json"}, 
                             events=events, active=True)
        if hook is None:
            msg = ("failed to create github webhook for {0}/{1} pointing to {2} with " 
                   "the {3} events").format(owner, repo, url, ", ".join(events))
            raise RuntimeError(msg)
    update = {}
    if hook.config['url'] != url:
        update['url'] = url
    if hook.config['content_type'] != 'json':
        update['content_type'] = 'json'
    if hook.events is None or set(hook.events) != set(events):
        update['events'] = events
    if not hook.active:
        update['active'] = True

    if len(update) > 0:
        status = hook.edit(**update)
        if not status:
            msg = ("failed to update github webhook for {0}/{1} pointing to {2} with " 
                   "the {3} events").format(owner, repo, url, ", ".join(events))
            raise RuntimeError(msg)

class PolyphemusPlugin(Plugin):
    """This class provides functionality for getting data from github."""

    requires = ('polyphemus.githubbase',)

    route = '/githubhook'

    request_methods = ['GET', 'POST']

    def setup(self, rc):
        hookurl = ("{0}/githubhook" if rc.port == 80 else \
                   "{0}:{1}/githubhook").format(rc.server_url, rc.port)
        verify_hook(rc.github_owner, rc.github_repo, hookurl, rc.github_events, 
                    user=rc.github_user, credfile=rc.github_credentials)

    _action_to_event = {'opened': 'github-pr-new', 'synchronize': 'github-pr-sync'}

    def response(self, rc):
        rawdata = json.loads(request.data)
        if 'pull_request' not in rawdata:
            return "\n", None
        action = rawdata['action']
        if action not in self._action_to_event:
            # Can be one of 'opened', 'closed', 'synchronize', or 'reopened', 
            # but we only care about "opened" and "synchronize".
            return "\n", None
        gh = GitHub()
        pr = gh.pull_request(rc.github_owner, rc.github_repo, rawdata['number'])
        event = Event(name=self._action_to_event[action], data=pr)
        return request.method + ": github\n", event

    @runfor(*_action_to_event.values())
    def execute(self, rc):
        """The github hook plugin is executed for 'github-pr-new' and 'github-pr-sync'
        events.  The event data must be either a github3 PullRequest object or a
        tuple of the form (owner, repository, number).
        """
        event = rc.event
        pr = event.data
        set_pull_request_status(pr, 'pending', target_url="", 
            description='patience, discipline', 
            user=rc.github_user, credfile=rc.github_credentials)
