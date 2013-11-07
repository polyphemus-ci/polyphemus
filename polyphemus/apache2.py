"""The plugin to setup polyphemus for use under the Apache 2 server.

This module is available as an polyphemus plugin by the name ``polyphemus.apache2``.

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
    WSGIScriptAlias / {wsgi_file}
</VirtualHost>
"""

wsgi_template = """import polyphemus.main
application = polyphemus.main.setup(rc={rc!r}).rc.app
"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for seting up Polyphemus to run 
    with Apache v2 and mod_wsgi.
    """

    requires = ('polyphemus.base',)

    defaultrc = RunControl(
        apache2_setup=False,
        server_name=NotSpecified,
        site_conf_file=NotSpecified,
        site_conf_file=NotSpecified,
        wsgi_file=NotSpecified,
        )

    rcdocs = {
        'apache2_setup': "Sets up polyphemus to run under Apache 2 with mod_wsgi.",
        'server_name': "The name of the website, e.g. 'polyphemus.org'."
        'site_conf_file': ("The Apache 2 site configiration file name, defaults to "
                           "'/etc/apache2/sites-available/{server_name}.conf'"),
        'wsgi_file': ("The WSGI script file name, defaults to "
                      "'/var/www/{appname}/{appname}.wsgi'"),
        }

    def update_argparser(self, parser):
        parser.add_argument('--apache2-setup', action='store_true', 
                            dest='apache2_setup', help=self.rcdocs['apache2_setup'])
        parser.add_argument('--no-apache2-setup', action='store_false', 
                            dest='apache2_setup', help="Doesn't s" + 
                                                    self.rcdocs['apache2_setup'][1:])
        parser.add_argument('--server-name', dest='server_name', 
                            help=self.rcdocs['server_name'])
        parser.add_argument('--site-conf-file', dest='site_conf_file', 
                            help=self.rcdocs['site_conf_file'])
        parser.add_argument('--wsgi-file', dest='wsgi_file', 
                            help=self.rcdocs['wsgi_file'])

    def setup(self, rc):
        if rc.server_name is NotSpecified:
            rc.server_name = rc.appname + '.com'
        if rc.site_conf_file is NotSpecified:
            scf = '/etc/apache2/sites-available/{0}.conf'
            rc.site_conf_file = scf.format(rc.server_name)
        rc.site_conf_file = os.path.abspath(rc.site_conf_file)
        if rc.wsgi_file is NotSpecified:
            rc.wsgi_file = '/var/www/{0}/{0}.wsgi'.format(rc.appname)
        rc.wsgi_file = os.path.abspath(rc.wsgi_file)
        if not rc.apache2_setup:
            return
        conf = conf_template.format(**rc)
        wsgi = wsgi_template.format(**rc)
        newoverwrite(conf, rc.site_conf_file, verbose=rc.verbose)
        newoverwrite(wsgi, rc.wsgi_file, verbose=rc.verbose)
