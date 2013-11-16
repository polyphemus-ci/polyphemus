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
curl --data '{{"status": "pending", "number": {number}, "description": "build and test initialized"}}' {server_url}:{port}/batlabstatus
"""

post_curl_template = """# polyphemus post_all callbacks
if [ -z $_NMI_STEP_FAILED ]
then
    curl --data '{{"status": "success", "number": {number}, "description": "build and test completed successfully"}}' {server_url}:{port}/batlabstatus
else
    curl --data '{{"status": "failure", "number": {number}, "description": "build and test failed"}}' {server_url}:{port}/batlabstatus
fi
"""

unzip_cmds_template = \
"""curl -L -o batlab_scripts.zip {batlab_scripts_url}
unzip -d {jobdir} batlab_scripts.zip
rm batlab_scripts.zip
ls {jobdir}"""

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
        task_file = '{0}/{1}.sh'.format(jobdir, task)
        client.exec_command('touch ' + task_file)
        client.exec_command('chmod 755 ' + task_file)
        client.exec_command('echo "{0} = {1}" >> {2}/{3}'.format(task, task_file, 
                                                          jobdir, run_spec_path))
    if not os.path.isabs(task_file) and not task_file.startswith('$'):
        task_file = jobdir + '/' + task_file
    return task_file


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
    
    @runfor('github-pr-new', 'github-pr-sync')
    def execute(self, rc):
        pr = rc.event.data  # pull request object
        job = pr.repository + (pr.number,)  # job key (owner, repo, number) 
        jobdir = "${HOME}/" + "--".join(job)
        jobs = PersistentCache(cachefile=rc.batlab_jobs_cache)

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
            msg = 'Error connecting to BaTLab'
            warn(msg, RuntimeWarning)
            rc.event = Event(name='batlab-status', data={'status': 'error', 
                             'number': pr.number, 'description': msg})
            return

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

        # Overwrite fetch file
        head_repo = github3.repository(*pr.head.repo)
        fetch = git_fetch_template.format(repo_url=head_repo.clone_url,
                                          repo_dir=job[1], branch=pr.head.label)
        cmd = 'echo "{0}" > {1}/{2}'.format(fetch, jobdir, rc.batlab_fetch_file)
        client.exec_command(cmd)

        # append callbacks to run spec
        _, x, _ = client.exec_command('cat {0}/{1}'.format(jobdir, rc.batlab_run_spec))
        run_spec_lines = [l.strip() for l in x.splitlines()]
        pre_file = _ensure_task_script('pre_all', run_spec_lines, rc.batlab_run_spec, 
                                       jobdir, client)
        pre_curl = pre_curl_template.format(number=pr.number, port=rc.port, 
                                            server_url=rc.server_url)
        client.exec_command('echo "{0}" >> {1}'.format(pre_curl, pre_file))
        post_file = _ensure_task_script('post_all', run_spec_lines, rc.batlab_run_spec,
                                        jobdir, client)
        post_curl = post_curl_template.format(number=pr.number, port=rc.port, 
                                              server_url=rc.server_url)
        client.exec_command('echo "{0}" >> {1}'.format(post_curl, post_file))

        # submit the job
        client.exec_command('cd ' + jobdir)
        _, submitout, _ = client.exec_command('{0} {1}'.format(rc.batlab_submit_cmd,
                                                               rc.batlab_run_spec))
        client.exec_command('cd ${HOME}')

        # clean up
        client.close()
        lines = submitout.out.splitlines()
        report_url = lines[-1].strip()
        gid = lines[0].split()[-1]
        jobs[job] = {'gid': gid, 'report_url': report_url, 'dir': jobdir}
        if rc.verbose:
            print("BaTLab reporting link: " + report_url)

