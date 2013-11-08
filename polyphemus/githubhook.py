"""The plugin to recieve posts from github and dispatch them to certain events.

This module is available as an polyphemus plugin by the name ``polyphemus.githubhook``.

BaTLaB Plugin API
=================
"""
from __future__ import print_function
import os
import sys
import pprint
import socket
from warnings import warn
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

def verify_hook(owner, repo, url, events):
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

    """
    gh = GitHub()
    r = gh.repository(owner, repo)
    for hook in r.iter_hooks():
        if hook.name is not 'web':
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

    requires = ('polyphemus.base',)

    defaultrc = RunControl(
        github_owner=NotSpecified,
        github_repo=NotSpecified,
        github_events=['pull_request'],
        )

    rcdocs = {
        'github_owner': "The repository owner on github, e.g. 'scopatz'",
        'github_repo': "The repository name on github, e.g. 'pyne'",
        'github_events': "The github events to trigger on.",
        }

    def update_argparser(self, parser):
        parser.add_argument('--github-owner', dest='github_owner',
                            help=self.rcdocs["github_owner"])
        parser.add_argument('--github-repo', dest='github_repo',
                            help=self.rcdocs["github_repo"])
        parser.add_argument('--github-events', nargs="+", dest='github_events',
                            help=self.rcdocs["github_events"])

    route = '/githubhook'

    request_methods = ['GET', 'POST']

    def setup(self, rc):
        if rc.github_owner is NotSpecified:
            raise ValueError('github_owner run control parameter must be specified '
                             'to use the githubhook plugin.')
        if rc.github_repo is NotSpecified:
            raise ValueError('github_repo run control parameter must be specified '
                             'to use the githubhook plugin.')
        hookurl = ("{0}/githubhook" if rc.port == 80 else \
                   "{0}:{1}/githubhook").format(rc.server_url, rc.port)
        verify_hook(rc.github_owner, rc.github_repo, hookurl, rc.github_events)

    def response(self, rc):
        print("computing response")
        print("request:", request.form.keys())
        #print("made payload:", request.form['payload'])
        #import pdb; pdb.set_trace()
        data = github3.events.Event.from_json(json.loads(request.form['payload']))
        print("made data:", data)
        event = Event(name='github', data=data)
        return request.method + ": github\n", event

    @runfor('github')    
    def execute(self, rc):
        event = rc.event
        pprint.pprint(event.data)
