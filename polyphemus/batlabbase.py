"""The basic functionality for BaTLab.

This module is available as an polyphemus plugin by the name `polyphemus.batlabbase`.

Basic BaTLaB API
=================
"""
from __future__ import print_function
import os
import sys
from tempfile import NamedTemporaryFile
import subprocess
from warnings import warn
from getpass import getuser, getpass

import paramiko

from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin
from .base import ssh_pub_key

if sys.version_info[0] >= 3:
    basestring = str

BATLAB_SUBMIT_HOSTNAME = 'submit-1.batlab.org'

class PolyphemusPlugin(Plugin):
    """This class provides basic BaTLab functionality."""

    requires = ('polyphemus.base',)

    defaultrc = RunControl(
        batlab_user=NotSpecified,
        )

    rcdocs = {
        'batlab_user': ("The BaTLab user name to login with.  Must have rights "
                        "on the submit node."),
        }

    def update_argparser(self, parser):
        parser.add_argument('--batlab-user', dest='batlab_user',
                            help=self.rcdocs["batlab_user"])

    def setup(self, rc):
        if rc.batlab_user is NotSpecified:
            user = getuser()
            print("batlab username not specified, found {0!r}".format(user))
            rc.batlab_user = user

        # make sure that we can authenticate in the future with SSH public keys
        key = paramiko.RSAKey(filename=rc.ssh_key_file)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #client.get_host_keys().add(BATLAB_SUBMIT_HOSTNAME, 'ssh-rsa', key)
        try:
            client.connect(BATLAB_SUBMIT_HOSTNAME, username=rc.batlab_user, 
                           key_filename=rc.ssh_key_file)
            client.close()
            can_connect = True
        except paramiko.AuthenticationException:
            can_connect = False
        except paramiko.BadHostKeyException:
            import pdb; pdb.set_trace()
            can_connect = False
        if not can_connect:
            password = False
            while not password:
                password = getpass("{0}@{1} password: ".format(rc.batlab_user, 
                                                        BATLAB_SUBMIT_HOSTNAME))
            pub = ssh_pub_key(rc.ssh_key_file)
            cmds = ["mkdir -p ~/.ssh",
                'echo "{0}" >> ~/.ssh/authorized_keys'.format(pub),
                'chmod og-rw ~/.ssh/authorized_keys',
                'chmod a-x ~/.ssh/authorized_keys',
                'chmod 700 ~/.ssh',
                ]
            client.connect(BATLAB_SUBMIT_HOSTNAME, username=rc.batlab_user, 
                           password=password)
            for cmd in cmds:
                stdin, stdout, stderr = client.exec_command(cmd)
            client.close()
            # verify thatthis key works
            client.connect(BATLAB_SUBMIT_HOSTNAME, username=rc.batlab_user, 
                           key_filename=rc.ssh_key_file)
            client.close()
            print("finished connecting")
        client.close()  # Just to be safe
