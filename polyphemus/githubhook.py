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

import github3.events
from flask import request

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin
from .event import Event, runfor

class PolyphemusPlugin(Plugin):
    """This class provides functionality for getting data from github."""

    requires = ('polyphemus.base',)

    defaultrc = RunControl(
        )

    route = '/githubhook'

    request_methods = ['GET', 'POST']

    def setup(self, rc):
        jsonip = urlopen('http://jsonip.com/')
        ipinfo = json.load(jsonip)
        ipaddr = ipinfo['ip']
        name, aliases, ips = socket.gethostbyaddr(ipaddr)
        hookurl = "http://{0}/githubhook" if rc.port == 80 else \
                  "http://{0}:{1}/githubhook"
        print("Please register the following URL with GitHub:\n\n"
              "  " + hookurl.format(name, rc.port) + "\n\n"
              "Otherwise please try any of the following:\n")
        for n in aliases + ips:
            print("  " + hookurl.format(n, rc.port) + "\n")

    def response(self, rc):
        data = github3.events.Event.from_json(request.form['payload'])
        event = Event(name='github', data=data)
        return request.method + ": github\n", event


    @runfor('github')    
    def execute(self, rc):
        event = rc.event
        pprint.pprint(event.data)
