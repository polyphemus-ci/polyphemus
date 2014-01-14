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

from .utils import RunControl, NotSpecified, writenewonly, newoverwrite, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin

if sys.version_info[0] >= 3:
    basestring = str

conf_template = """
ServerName {server_name}

<VirtualHost {server_name}:{port}>
    ServerAlias www.{server_name}
    WSGIScriptAlias / {wsgi_file}
    DocumentRoot {rc_dir}

<Directory {wsgi_dir}>
        Order allow,deny
        Allow from all
    </Directory>


     # ---- Configure Logging ----

    ErrorLog {log_dir}/error.log
    LogLevel info
    CustomLog {log_dir}/access.log combined


</VirtualHost>
"""

port_template = """
# If you just change the port or add more ports here, you will likely also
# have to change the VirtualHost statement in
# /etc/apache2/sites-enabled/000-default

Listen 80

Listen {port}

<IfModule ssl_module>
	Listen 443
</IfModule>

<IfModule mod_gnutls.c>
	Listen 443
</IfModule>

"""

wsgi_template = """import polyphemus.main
import sys
sys.stdout = sys.stderr
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
        wsgi_file=NotSpecified,
        )

    rcdocs = {
        'apache2_setup': "Sets up polyphemus to run under Apache 2 with mod_wsgi.",
        'server_name': "The name of the website, e.g. 'polyphemus.org'.",
        'site_conf_file': ("The Apache 2 site configiration file name, defaults to "
                           "'/etc/apache2/sites-available/{server_name}.conf'"),
        'wsgi_file': ("The WSGI script file name, defaults to "
                      "'/var/www/{appname}/{appname}.wsgi'"),
        'port_file': ("The Apache 2 ports.conf file, defaults to /etc/apache2/ports.conf"),
        'log_dir': ("The directory for apache logging, defaults to /apache-logs")
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
        parser.add_argument('--port-file',dest='port_file',
                            help=self.rcdocs['port_file'])
        parser.add_argument('--log-dir',dest='log_dir',
                            help=self.rcdocs['log_dir'])

    def setup(self, rc):
        if rc.server_name is NotSpecified:
            rc.server_name = rc.appname + '.com'
        if rc.site_conf_file is NotSpecified:
            scf = '/etc/apache2/sites-available/{0}.conf'
            rc.site_conf_file = scf.format(rc.server_name)
        rc.site_conf_file = os.path.abspath(rc.site_conf_file)
        if rc.wsgi_file is NotSpecified:
            rc.wsgi_file = '/var/www/{0}/{0}.wsgi'.format(rc.server_name)
        rc.wsgi_file = os.path.abspath(rc.wsgi_file)
        if rc.log_dir is NotSpecified:
            rc.log_dir = '/apache-logs'
        if rc.port_file is NotSpecified:
            rc.port_file = '/etc/apache2/ports.conf'
        if not rc.apache2_setup:
            return
        conf = conf_template.format(port=rc.port, server_name=rc.server_name, 
                                    wsgi_file=rc.wsgi_file, rc_dir=rc.rc.rsplit('/',1)[0],
                                    wsgi_dir=rc.wsgi_file.rsplit('/',1)[0], log_dir=rc.log_dir )
        wsgi = wsgi_template.format(rc=rc.rc)
        ports = port_template.format(port=rc.port)
        newoverwrite(conf, rc.site_conf_file, verbose=rc.verbose)
        newoverwrite(wsgi, rc.wsgi_file, verbose=rc.verbose)
        if os.path.isfile(rc.port_file):
            port_file = open(rc.port_file,'r')
            port_lines = port_file.readlines()
            port_file.close()
            found = False
            for line in port_lines:
                tokens = line.split()
                if len(tokens) == 2:
                    if tokens[0] == 'Listen' and tokens[1] == str(rc.port):
                        found = True
            if not found:
                port_file = open(rc.port_file,'a')
                port_file.write('\nListen '+str(rc.port)+'\n')
                port_file.close()
              
        else:
            newoverwrite(ports, rc.port_file, verbose=rc.verbose)
