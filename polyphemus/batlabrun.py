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
curl --data "$_NMI_GID Succeeded"  {ip}:{port}
else
curl --data "$_NMI_GID Failed"  {ip}:{port}
fi
"""


class PolyphemusPlugin(Plugin):
    """This class provides functionality for running batlab."""

    requires = ('polyphemus.batlabbase',)

    defaultrc = RunControl(
        )

    route = '/batlabrun'

    def response(self, rc):
        print("I am batlab!")
        return "No you are batlab!\n", None

    @runfor('batlab')
    def execute(self, rc):
        fetch = fetch_template.format(repo="git://github.com/cyclus/cyclus", 
                                      branch="staging")

	curl = curl_template.format(ip='198.101.154.53',port='5000')

        fetchfile = NamedTemporaryFile()
        fetchfile.write(fetch)
        fetchfile.flush()
        subprocess.check_call(['scp', fetchfile.name, 'cyclusci@submit-1.batlab.org:polyphemus/'])
        fetchfile.close()


	batlab_uid='cyclusci@submit-1.batlab.org'
	test_dir= 'polyphemus;'
	test_subdir='cyclus_runs'
	test_deps='CYCLUS fetch CYCAMORE cycamore.polyphemus.run-spec submit.sh'
	replace_file = 'fetch/cyclus.git'
	run_spec='cycamore.polyphemus.run-spec'
	sub_cmd='./submit.sh'
	#assumes polyphemus on batlab is altered version of main ci dir
        rtn, out = check_cmd(['ssh', batlab_uid, \
				'cd',test_dir+';', \
				'git','pull;',\
				'mkdir',test_subdir+'/'+fetchfile.name+';', \
				'cp','-R '+test_deps+' '+test_subdir+'/'+fetchfile.name+';', \
				'mv',fetchfile.name+' 'test_subdir+'/'+fetchfile.name+'/'+replace_file+';', \
				'rm',' -f '+fetchfile.name+';', \
				'cd',test_subdir+'/'+fetchfile.name+';', \
                                'echo','"'+curl+'"'+" >>`cat "+run_spec+" | grep post_all |sed -e 's/ //g' | sed -e 's/post_all=//g'`;", \
				sub_cmd, run_spec])
        lines = out.splitlines()
        report_url = lines[-1].strip()
        print(report_url)
