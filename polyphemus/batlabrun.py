"""The plug in to run on batlab.

This module is available as an polyphemus plugin by the name ``polyphemus.batlabrun``.

BaTLaB Plugin API
=================
"""
from __future__ import print_function
import os
import sys
from tempfile import NamedTemporaryFile
import subprocess
from warnings import warn

from event import runfor

import paramiko
from .utils import RunControl, NotSpecified, writenewonly, \
    DEFAULT_RC_FILE, DEFAULT_PLUGINS, nyansep, indent, check_cmd
from .plugins import Plugin

if sys.version_info[0] >= 3:
    basestring = str

fetch_template = \
"""method = git
git_repo = {repo}
git_path = cyclus;cd cyclus;git checkout {branch}
"""
curl_template= \
"""
if [ -z $_NMI_STEP_FAILED ]
then
    curl --data "$_NMI_GID Succeeded"  {ip}:{port}/batlabstatus
else
    curl --data "$_NMI_GID Failed"  {ip}:{port}/batlabstatus
fi
"""

jobs = {}

class PolyphemusPlugin(Plugin):
    """This class provides functionality for running batlab."""



    requires = ('polyphemus.batlabbase',)

    defaultrc = RunControl(
        batlab_user='cyclusci',
        test_dir= 'polyphemus;',
        test_subdir='cyclus_runs',
        test_deps='CYCLUS fetch CYCAMORE cycamore.polyphemus.run-spec submit.sh',
        replace_file = 'fetch/cyclus.git',
        run_spec='cycamore.polyphemus.run-spec',
        sub_cmd='./submit.sh',      
        ssh_key_file='~/.ssh/id_rsa')


    route = '/batlabrun'

    def response(self, rc):
        print("I am batlab!")
        return "No you are batlab!\n", None

    @runfor('batlab')
    def execute(self, rc):
        fetch = fetch_template.format(repo="git://github.com/cyclus/cyclus", 
                                      branch="staging")

        curl = curl_template.format(ip=rc.server_url,port=rc.port)

        fetchfile = NamedTemporaryFile()
        fetchfile.write(fetch)
        fetchfile.flush()


        #assumes polyphemus on batlab is altered version of main ci dir


        client = paramiko.SSHClient()
        try:
            client.connect(BATLAB_SUBMIT_HOSTNAME, username=rc.batlab_user,key_filename=rc.ssh_key_file)

            if (rc.batlab_user,rc.repo,rc.branch) in jobs:
                client.exec_command('nmi_rm '+ jobs((rc.batlab_user,rc.repo,rc.branch))
                del jobs((rc.batlab_user,rc.repo,rc.branch))

            client.put(fetchfile.name,rc.test_dir)

            client.exec_command('cd '+rc.test_dir)
            client.exec_command('git pull')
            client.exec_command('mkdir '+rc.test_subdir+'/'+fetchfile.name)
            client.exec_command('cp -R '+rc.test_deps+' '+rc.test_subdir+'/'+fetchfile.name)
            client.exec_command('mv '+fetchfile.name+' 'rc.test_subdir+'/'+fetchfile.name+'/'+rc.replace_file)
            client.exec_command('rm -f '+fetchfile.name)
            client.exec_command('cd '+rc.test_subdir+'/'+fetchfile.name)
            client.exec_command( 'echo "'+curl+'"'+" >>`cat "+rc.run_spec+" | grep post_all |sed -e 's/ //g' | sed -e 's/post_all=//g'`")
            stdin, stdout, stderr = client.exec_command(rc.sub_cmd+' '+rc.run_spec)

            lines = stdout.out.splitlines()
            report_url = lines[-1].strip()
            gid = lines[0].split()[-1]
            jobs[(rc.batlab_user,rc.repo,rc.branch)]=gid
            client.close()
            print(report_url)

        except:
            print('Error talking to BATLAB')


        fetchfile.close()
