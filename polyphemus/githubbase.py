"""The plugin to interact with github.

This module is available as an polyphemus plugin by the name `polyphemus.githubbase`.

GitHub Basic API
=================
"""
from __future__ import print_function
import os
import io
import sys
import pprint
import socket
from warnings import warn
from collections import Sequence
from getpass import getuser, getpass
from tempfile import NamedTemporaryFile

if sys.version_info[0] >= 3:
    basestring = str

try:
    import simplejson as json
except ImportError:
    import json

from github3 import GitHub, pull_request, repository
import github3.events
from flask import request

from .utils import RunControl, NotSpecified, writenewonly, newoverwrite, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin
from .event import Event, runfor

def gh_make_token(gh, user, credfile='gh.cred'):
    """Creates a github token for the user.

    Parameters
    ----------
    gh : GitHub object
        The object to authenticate with.
    user : str
        The username to make the token for.
    credfile : str, optional
        The github credentials file name.
    
    """
    password = False
    while not password:
        password = getpass("{0}'s github password: ".format(user))
    note = 'polyphemus application'
    note_url = 'polyphemus.org'
    scopes = ['user', 'repo']
    auth = gh.authorize(user, password, scopes, note, note_url)
    newoverwrite(str(auth.token) + '\n' + str(auth.id) + '\n', credfile)

def ensure_logged_in(gh, user=None, credfile='gh.cred'):
    """Ensures that the user is logged in, either through a token or by 
    creating a token.

    Parameters
    ----------
    gh : GitHub object
        The object to authenticate with.
    user : str, None, or NotSpecified, optional
        The username to log into github with
    credfile : str, optional
        The github credentials file name.
    """
    if user is None or user is NotSpecified:
        user = getuser()
        print("github username not specified, found {0!r}".format(user))
    if not os.path.isfile(credfile):
        gh_make_token(gh, user, credfile=credfile)
    with io.open(credfile, 'r') as f:
        token = f.readline().strip()  
        id = f.readline().strip()
    gh.login(username=user, token=token)

_stat_key = lambda s: s.created_at

def get_pull_request_status(gh, r, pr):
    """Sets a state for every commit associated with a pull request.

    Parameters
    ----------
    gh : GitHub
        A logged in GitHub instance
    r : Repository
        A github3 repository objects
    pr : PullRequest or len-3 sequence
        A github3 pull request object or a tuple of (owner, repository, number).

    Returns
    -------
    status : Status or None
        The latest pull request status or None

    """
    if isinstance(pr, Sequence):
        pr = gh.pull_request(*pr)
    statuses = sorted(r.iter_statuses(pr.head.sha), key=_stat_key)
    if len(statuses) == 0:
        return None
    return statuses[-1]

def set_pull_request_status(pr, state, target_url="", description='', user=None, 
                            credfile='gh.cred'):
    """Sets a state for every commit associated ith a pull request.

    Parameters
    ----------
    pr : PullRequest or len-3 sequence
        A github3 pull request object or a tuple of (owner, repository, number).
    state : str
        Accepted values are 'pending', 'success', 'error', 'failure'.
    target_url : str, optional
        URL to link with this status.
    description : str, optional
        Flavor text.
    user : str, None, or NotSpecified, optional
        The username to log into github with.
    credfile : str, optional
        The github credentials file name.

    """
    gh = GitHub()
    ensure_logged_in(gh, user=user, credfile=credfile)
    if isinstance(pr, Sequence):
        r = gh.repository(*pr[:2])
        pr = gh.pull_request(*pr)
    else:
        r = gh.repository(*pr.repository)
    status = r.create_status(pr.head.sha, state=state, target_url=target_url, 
                             description=description)    

class PolyphemusPlugin(Plugin):
    """This class provides basic functionality for github interactions."""

    requires = ('polyphemus.base',)

    defaultrc = RunControl(
        github_owner=NotSpecified,
        github_repo=NotSpecified,
        github_events=['pull_request'],
        github_user=NotSpecified,
        github_credentials='gh.cred',
        )

    rcdocs = {
        'github_owner': "The repository owner on github, e.g. 'scopatz'",
        'github_repo': "The repository name on github, e.g. 'pyne'",
        'github_events': "The github events to trigger on.",
        'github_user': ("The github user name to login with.  Must have rights "
                        "to the repo."),
        'github_credentials': ("The github credentials file where token "
                               "authentication is stored."),
        }

    def update_argparser(self, parser):
        parser.add_argument('--github-owner', dest='github_owner',
                            help=self.rcdocs["github_owner"])
        parser.add_argument('--github-repo', dest='github_repo',
                            help=self.rcdocs["github_repo"])
        parser.add_argument('--github-events', nargs="+", dest='github_events',
                            help=self.rcdocs["github_events"])
        parser.add_argument('--github-user', dest='github_user',
                            help=self.rcdocs["github_user"])
        parser.add_argument('--github-credentials', dest='github_credentials',
                            help=self.rcdocs["github_credentials"])

    def setup(self, rc):
        if rc.github_owner is NotSpecified:
            raise ValueError('github_owner run control parameter must be specified '
                             'to use the githubhook plugin.')
        if rc.github_repo is NotSpecified:
            raise ValueError('github_repo run control parameter must be specified '
                             'to use the githubhook plugin.')
