"""The plug in to run on batlab.

This module is available as an polyphemus plugin by the name ``polyphemus.batlabrun``.

BaTLaB Plugin API
=================
"""
from __future__ import print_function
import os
import sys
import socket
import subprocess
from warnings import warn

import github3
import paramiko

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor
from .batlabbase import BATLAB_SUBMIT_HOSTNAME

if sys.version_info[0] >= 3:
    basestring = str

git_fetch_template = \
"""method = git
git_repo = {repo_url}
git_path = {repo_dir};cd {repo_dir};git checkout {branch}
"""

pre_curl_template = r"""# polyphemus pre_all callback
curl --form status='{{\"status\":\"pending\",\"number\":{number},\"description\":\"build and test initialized\"}}' {server_url}:{port}/batlabstatus
"""

post_curl_template = r"""# polyphemus post_all callbacks
if [ -z $_NMI_STEP_FAILED ]
then
    curl --form status='{{\"status\":\"success\",\"number\":{number},\"description\":\"build and test completed successfully\"}}' {server_url}:{port}/batlabstatus
else
    curl --form status='{{\"status\":\"failure\",\"number\":{number},\"description\":\"build and test failed\"}}' {server_url}:{port}/batlabstatus
fi
"""

unzip_cmds_template = \
"""curl -L -o batlab_scripts.zip {batlab_scripts_url}
unzip -d {jobdir} batlab_scripts.zip
rm batlab_scripts.zip
ls {jobdir}"""

jobdir_scp_template = \
"""method = scp
scp_file = {jobdir}/*
recursive = true
"""

def _find_startswith(x, s):
    """Finds the index of a sequence that starts with s or returns -1.
    """
    for i, elem in enumerate(x):
        if elem.startswith(s):
            return i
    return -1

def _ensure_task_script(task, run_spec_lines, run_spec_path, jobdir, client):
    i = _find_startswith(run_spec_lines, task)
    if i >= 0:
        task_file = run_spec_lines[i].split('=', 1)[1].strip()
    else:
        task_file = '{0}.sh'.format(task)
        client.exec_command("echo '#!/bin/bash' > {0}/{1}".format(jobdir, task_file))
        client.exec_command('chmod 755 {0}/{1}'.format(jobdir, task_file))
        client.exec_command('echo "{0} = {1}" >> {2}/{3}'.format(task, task_file, 
                                                          jobdir, run_spec_path))
    return task_file

def _ensure_runspec_option(option, run_spec_lines, run_spec_path, jobdir, client, value):
    i = _find_startswith(run_spec_lines, option)
    if i >= 0:
        old_val = run_spec_lines[i].split('=', 1)[1].strip()
        if old_val != value:
            client.exec_command("sed -i -e 's/{0}/{1}={2}/g' {3}/{4}".format(run_spec_lines[i], 
                                                          option, value, jobdir, run_spec_path))
    else:
        client.exec_command('echo "{0} = {1}" >> {2}/{3}'.format(option, value, 
                                                          jobdir, run_spec_path))


class PolyphemusPlugin(Plugin):
    """This class provides functionality for running batlab."""

    requires = ('polyphemus.batlabbase',)

    defaultrc = RunControl(
        batlab_jobs_cache='jobs.cache', 
        batlab_submit_cmd='nmi_submit',
        batlab_kill_cmd='nmi_rm',
        batlab_scripts_url=NotSpecified,
        batlab_fetch_file=NotSpecified,
        batlab_run_spec=NotSpecified,
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
        'batlab_fetch_file': ("The fetch file that is used by BaTLab to grab the "
                              "project source code.  This file will be overwritten "
                              "by polyphemus. This should be a relative path from "
                              "the base of the batlab_scripts_url dir."),
        'batlab_run_spec': ("The top level *.run-spec file that is submitted to "
                            "BaTLab. This should be a relative path from "
                            "the base of the batlab_scripts_url dir."),
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
        parser.add_argument('--batlab-fetch-file', dest='batlab_fetch_file',
                            help=self.rcdocs["batlab_fetch_file"])
        parser.add_argument('--batlab-run-spec', dest='batlab_run_spec',
                            help=self.rcdocs["batlab_run_spec"])

    def setup(self, rc):
        if rc.batlab_scripts_url is NotSpecified:
            raise ValueError('batlab_scripts_url must be provided!')
        if not (rc.batlab_scripts_url.endswith('.git') or 
                rc.batlab_scripts_url.endswith('.zip')):
            raise ValueError("batlab_scripts_url must end in '.git' or '.zip', "
                             "found {0!r}".format(rc.batlab_scripts_url))
        if rc.batlab_fetch_file is NotSpecified:
            raise ValueError('batlab_fetch_file must be provided!')
        if rc.batlab_run_spec is NotSpecified:
            raise ValueError('batlab_run_spec must be provided!')
    
    @runfor('batlab-run', 'github-pr-new', 'github-pr-sync')
    def execute(self, rc):
        event_name = rc.event.name
        pr = rc.event.data  # pull request object
        job = pr.repository + (pr.number,)  # job key (owner, repo, number) 
        jobdir = "${HOME}/" + "--".join(pr.repository + (str(pr.number),))
        jobs = PersistentCache(cachefile=rc.batlab_jobs_cache)
        event = rc.event = Event(name='batlab-status', data={'status': 'error', 
                                 'number': pr.number, 'description': ''})

        # connect to batlab
        key = paramiko.RSAKey(filename=rc.ssh_key_file)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #client.get_host_keys().add(BATLAB_SUBMIT_HOSTNAME, 'ssh-rsa', key)
        try:
            client.connect(BATLAB_SUBMIT_HOSTNAME, username=rc.batlab_user,
                           key_filename=rc.ssh_key_file)
        except (paramiko.BadHostKeyException, paramiko.AuthenticationException, 
                paramiko.SSHException, socket.error):
            msg = 'Error connecting to BaTLab.'
            warn(msg, RuntimeWarning)
            event.data['description'] = msg
            return

        # if sync event, kill an existing job.
        if event_name == 'github-pr-sync' and job in jobs:
            try:
                client.exec_command(rc.batlab_kill_cmd + ' ' + jobs[job]['gid'])
            except paramiko.SSHException:
                event.data['description'] = "Error killing existing BaTLab job."
                return
            del jobs[job]

        # make sure we have a clean jobdir
        client.exec_command('rm -rf ' + jobdir)

        # put the scripts on batlab in a '~/owner--reposiotry--number' dir
        if rc.batlab_scripts_url.endswith('.git'):
            cmd = 'git clone {0} {1}'.format(rc.batlab_scripts_url, jobdir)
            try:
                client.exec_command(cmd)
            except paramiko.SSHException:
                event.data['description'] = "Error cloning BaTLab scripts."
                return            
        elif rc.batlab_scripts_url.endswith('.zip'):
            cmds = unzip_cmds_template.format(jobdir=jobdir, 
                    batlab_scripts_url=rc.batlab_scripts_url).splitlines()
            try:
                rtns = list(map(client.exec_command, cmds))
            except paramiko.SSHException:
                event.data['description'] = "Error unzipping BaTLab scripts."
                return            
            ls = rtns[-1][1].read().split()
            if len(ls) == 1:
                try:
                    client.exec_command('mv {0}/{1}/* {0}'.format(jobdir, ls[0]))
                except paramiko.SSHException:
                    event.data['description'] = "Error moving BaTLab scripts."
                    return            
        else:
            raise ValueError("rc.batlab_scripts_url not understood.")

        # Overwrite fetch file
        head_repo = github3.repository(*pr.head.repo)
        fetch = git_fetch_template.format(repo_url=head_repo.clone_url,
                                          repo_dir=job[1], branch=pr.head.ref)
        cmd = 'echo "{0}" > {1}/{2}'.format(fetch, jobdir, rc.batlab_fetch_file)
        try:
            client.exec_command(cmd)
        except paramiko.SSHException:
            event.data['description'] = "Error overwritting fetch file."
            return
        
        # append callbacks to run spec
        try:
            _, x, _ = client.exec_command('cat {0}/{1}'.format(jobdir, 
                                                               rc.batlab_run_spec))
            run_spec_lines = [l.strip() for l in x.readlines()]
            pre_file = _ensure_task_script('pre_all', run_spec_lines, 
                                           rc.batlab_run_spec, jobdir, client)
            pre_curl = pre_curl_template.format(number=pr.number, port=rc.port, 
                                                server_url=rc.server_url)
            client.exec_command('echo "{0}" >> {1}/{2}'.format(pre_curl, 
                                                               jobdir, pre_file))
            post_file = _ensure_task_script('post_all', run_spec_lines, 
                                            rc.batlab_run_spec, jobdir, client)
            _ensure_runspec_option('always_run_post_all', run_spec_lines, 
                                   rc.batlab_run_spec, jobdir, client, 'true')
            post_curl = post_curl_template.format(number=pr.number, port=rc.port, 
                                                  server_url=rc.server_url)
            client.exec_command('echo "{0}" >> {1}/{2}'.format(post_curl, jobdir, 
                                                               post_file))
        except paramiko.SSHException:
            event.data['description'] = "Error appending BaTLab callbacks."
            return            

        # create scp for jobdir
        jobdir_scp = jobdir_scp_template.format(jobdir=jobdir)
        cmd = 'echo "{0}" >> {1}/jobdir.scp'.format(jobdir_scp, jobdir)
        try:
            client.exec_command(cmd)
        except paramiko.SSHException:
            event.data['description'] = "Error creating jobdir.scp file."
            return            
        inputs = run_spec_lines[_find_startswith(run_spec_lines, 'inputs')].strip()
        if len(inputs.split('=', 1)[-1].strip()) > 0:
            cmd = "sed -i 's:{0}:{0},jobdir.scp:' {1}/{2}"
        else:
            cmd = "sed -i 's:{0}:jobdir.scp:' {1}/{2}"
        try:
            client.exec_command(cmd.format(inputs, jobdir, rc.batlab_run_spec))
        except paramiko.SSHException:
            event.data['description'] = "Error adding jobdir.scp to inputs."
            return            

        # submit the job
        cmd = 'cd {0}; {1} {2}'
        cmd = cmd.format(jobdir, rc.batlab_submit_cmd, rc.batlab_run_spec)
        try:
            _, submitout, submiterr = client.exec_command(cmd)
        except paramiko.SSHException:
            event.data['description'] = "Error submitting BaTLab job."
            return
        err = submiterr.read().strip()
        if 0 < len(err):
            event.data['description'] = err
            warn("BaTLab job unsuccessfully submitted:\n" + err, RuntimeWarning)
            return

        # clean up
        lines = submitout.readlines()
        #import pprint
        #pprint.pprint(lines)
        #pprint.pprint(submiterr.read())
        report_url = lines[-1].strip()
        gid = lines[0].split()[-1]
        client.close()
        jobs[job] = {'gid': gid, 'report_url': report_url, 'dir': jobdir}
        if rc.verbose:
            print("BaTLab reporting link: " + report_url)
        event.data.update(status='pending', description="BaTLab job submitted.",
                          target_url=report_url)

