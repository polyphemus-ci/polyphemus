"""The plugin to setup polyphemus for use under the Apache 2 server.

This module is available as an polyphemus plugin by the name ``polyphemus.batlabrun``.

BaTLaB Plugin API
=================
"""
from __future__ import print_function
import os
import sys
from warnings import warn

from event import runfor

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin

if sys.version_info[0] >= 3:
    basestring = str

conf_template = """<VirtualHost *:{port}>
    ServerName {sever_name}
    ServerAlias www.{server_name}
    WSGIScriptAlias / /var/www/polyphemus/polyphemus.wsgi
</VirtualHost>
"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for seting up Polyphemus to run 
    with Apache v2 and mod_wsgi.
    """

    requires = ('polyphemus.modwsgi',)

    defaultrc = RunControl(
        apache2_setup=False,
        server_name=NotSpecified,
        )

    rcdocs = {
        'apache2_setup': "Sets up polyphemus to run under Apache 2 with mod_wsgi",
        'server_name': "The name of the website, e.g. 'polyphemus.org'."
        }

    def update_argparser(self, parser):
        parser.add_argument('--rc', help=self.rcdocs['rc'])    

    def setup(self, rc):
        if rc.server_name is NotSpecified:
            rc.server_name = rc.appname + '.com'
        if not rc.apache2_setup:
            return
