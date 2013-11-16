"""The plug in to run on batlab.

This module is available as an polyphemus plugin by the name ``polyphemus.batlabrun``.

BaTLaB Plugin API
=================
"""
from __future__ import print_function
import os
import sys
import socket
from tempfile import NamedTemporaryFile
import subprocess
from warnings import warn

import paramiko

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor
from .batlabbase import BATLAB_SUBMIT_HOSTNAME

if sys.version_info[0] >= 3:
    basestring = str

fetch_template = \
"""method = git
git_repo = {repo}
git_path = cyclus;cd cyclus;git checkout {branch}
"""

curl_template = \
"""if [ -z $_NMI_STEP_FAILED ]
then
    curl --data "$_NMI_GID Succeeded"  {server_url}:{port}/batlabstatus
else
    curl --data "$_NMI_GID Failed"  {server_url}:{port}/batlabstatus
fi
"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for running batlab."""

    requires = ('polyphemus.batlabbase',)

    defaultrc = RunControl(
        test_dir= 'polyphemus;',
        test_subdir='cyclus_runs',
        test_deps='CYCLUS fetch CYCAMORE cycamore.polyphemus.run-spec submit.sh',
        replace_file = 'fetch/cyclus.git',
        run_spec='cycamore.polyphemus.run-spec',
        batlab_submit_cmd='./submit.sh',
        batlab_jobs_cache='jobs.cache', 
        )

    rcdocs = {
        'batlab_jobs_cache': 'The cache file for currently running BaTLab jobs.',
        }

    def update_argparser(self, parser):
        parser.add_argument('--batlab-jobs-cache', dest='batlab_jobs_cache',
                            help=self.rcdocs["batlab_jobs_cache"])

    @runfor('github-pr-new', 'github-pr-sync')
    def execute(self, rc):
        pr = rc.event.data  # pull request object
        job = pr.repository + (pr.number,)  # job key (owner, repo, number) 
        fetch = fetch_template.format(repo="git://github.com/cyclus/cyclus", 
                                      branch="staging")

        curl = curl_template.format(server_url=rc.server_url, port=rc.port)

        fetchfile = NamedTemporaryFile()
        fetchfile.write(fetch)
        fetchfile.flush()

        # connect to batlab
        key = paramiko.RSAKey(filename=rc.ssh_key_file)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.get_host_keys().add(BATLAB_SUBMIT_HOSTNAME, 'ssh-rsa', key)
        try:
            client.connect(BATLAB_SUBMIT_HOSTNAME, username=rc.batlab_user,
                           key_filename=rc.ssh_key_file)
        except (paramiko.BadHostKeyException, paramiko.AuthenticationException, 
                paramiko.SSHException, socket.error):
            msg = 'Error connecting to BaTLab'
            warn(msg, RuntimeWarning)
            rc.event = Event(name='batlab-status', data={'status': 'error', 
                             'number': pr.number, 'description': msg})
            return

        # get cache
        jobs = PersistentCache(cachefile=rc.batlab_jobs_cache)

        # if sync event, kill an existing job.
        if rc.event.name == 'github-pr-sync' and job in jobs:
            client.exec_command('nmi_rm '+ jobs[job]['gid'])
            del jobs[job]

        # FIXME SSHClient does not have a put() method.
        # use echo "..." >> filename instead
        #client.put(fetchfile.name, rc.test_dir)

        client.exec_command('cd '+rc.test_dir)
        client.exec_command('git pull')
        client.exec_command('mkdir '+rc.test_subdir+'/'+fetchfile.name)
        client.exec_command('cp -R '+rc.test_deps+' '+rc.test_subdir+'/'+fetchfile.name)
        client.exec_command('mv '+fetchfile.name+' 'rc.test_subdir+'/'+fetchfile.name+'/'+rc.replace_file)
        client.exec_command('rm -f '+fetchfile.name)
        client.exec_command('cd '+rc.test_subdir+'/'+fetchfile.name)
        client.exec_command( 'echo "' + curl+'"'+" >>`cat "+rc.run_spec+" | grep post_all |sed -e 's/ //g' | sed -e 's/post_all=//g'`")
        stdin, stdout, stderr = client.exec_command(rc.sub_cmd+' '+rc.run_spec)

        lines = stdout.out.splitlines()
        report_url = lines[-1].strip()
        gid = lines[0].split()[-1]
        jobs[job] = {'gid': gid, 'report_url': report_url}
        client.close()
        print(report_url)


        fetchfile.close()
