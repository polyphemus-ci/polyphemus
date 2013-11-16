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

unzip_cmds_template = \
"""curl -L -o batlab_scripts.zip {batlab_scripts_url}
unzip -d {jobdir} batlab_scripts.zip
rm batlab_scripts.zip
ls {jobdir}"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for running batlab."""

    requires = ('polyphemus.batlabbase',)

    defaultrc = RunControl(
        batlab_jobs_cache='jobs.cache', 
        batlab_submit_cmd='nmi_submit',
        batlab_kill_cmd='nmi_rm',
        batlab_scripts_url=NotSpecified,
        test_dir= 'polyphemus;',
        test_subdir='cyclus_runs',
        test_deps='CYCLUS fetch CYCAMORE cycamore.polyphemus.run-spec submit.sh',
        replace_file = 'fetch/cyclus.git',
        run_spec='cycamore.polyphemus.run-spec',
        )

    rcdocs = {
        'batlab_jobs_cache': 'The cache file for currently running BaTLab jobs.',
        'batlab_submit_cmd': 'The command that is used to submit jobs to BaTLab.', 
        'batlab_kill_cmd': 'The command that is used to kill existing jobs on BaTLab.',
        'batlab_scripts_url': ("This is the URL where the BaTLab files may be found. "
                               "If this ends in '.git' then it is interperted as a "
                               "git repository and the whole repo is cloned.  If "
                               "this ends in '.zip' then the URL is downloaded and "
                               "unpacked."),
        }

    def update_argparser(self, parser):
        parser.add_argument('--batlab-jobs-cache', dest='batlab_jobs_cache',
                            help=self.rcdocs["batlab_jobs_cache"])
        parser.add_argument('--batlab-submit-cmd', dest='batlab_submit_cmd',
                            help=self.rcdocs["batlab_submit_cmd"])
        parser.add_argument('--batlab-kill-cmd', dest='batlab_kill_cmd',
                            help=self.rcdocs["batlab_kill_cmd"])
        parser.add_argument('--batlab-scripts-url', dest='batlab_scripts_url',
                            help=self.rcdocs["batlab_scripts_url"])

    def setup(self, rc):
        if rc.batlab_scripts_url is NotSpecified:
            raise ValueError('batlab_scripts_url must be provided!')
        if not (rc.batlab_scripts_url.endswith('.git') or 
                rc.batlab_scripts_url.endswith('.zip')):
            raise ValueError("batlab_scripts_url must end in '.git' or '.zip', "
                             "found {0!r}".format(rc.batlab_scripts_url))
    
    @runfor('github-pr-new', 'github-pr-sync')
    def execute(self, rc):
        pr = rc.event.data  # pull request object
        job = pr.repository + (pr.number,)  # job key (owner, repo, number) 
        jobdir = "${HOME}/" + "--".join(*job)
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
            client.exec_command(rc.batlab_kill_cmd + ' ' + jobs[job]['gid'])
            client.exec_command('rm -r ' + jobdir)
            del jobs[job]

        # put the scripts on batlab in a '~/owner--reposiotry--number' dir
        if rc.batlab_scripts_url.endswith('.git'):
            cmd = 'git clone {0} {1}'.format(rc.batlab_scripts_url, jobdir)
            client.exec_command(cmd)
        elif rc.batlab_scripts_url.endswith('.zip'):
            cmds = unzip_cmds_template.format(jobdir=jobdir, 
                    batlab_scripts_url=rc.batlab_scripts_url).splitlines()
            rtns = list(map(client.exec_command, cmds))
            ls = rtns[-1][0].split()
            if len(ls) == 1:
                client.exec_command('mv {0}/{1}/* {0}'.format(jobdir, ls[0]))
        else:
            raise ValueError("rc.batlab_scripts_url not understood.")

        # FIXME SSHClient does not have a put() method.
        # use echo "..." >> filename instead
        #client.put(fetchfile.name, rc.test_dir)

        client.exec_command('cd ' + rc.test_dir)
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
        jobs[job] = {'gid': gid, 'report_url': report_url, 'dir': jobdir}
        client.close()
        print(report_url)


        fetchfile.close()
