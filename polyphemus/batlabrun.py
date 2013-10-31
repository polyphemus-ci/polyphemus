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
#from .version import report_versions

if sys.version_info[0] >= 3:
    basestring = str

fetch_template = \
"""method = git
git_repo = {repo}
git_path = cyclus;cd cyclus;git checkout {branch}
"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for running batlab."""

    defaultrc = RunControl(
        )

    @runfor('batlab')
    def execute(self, rc):
        fetch = fetch_template.format(repo="git://github.com/cyclus/cyclus", 
                                      branch="staging")
        fetchfile = NamedTemporaryFile()
        fetchfile.write(fetch)
        fetchfile.flush()
        subprocess.check_call(['scp', fetchfile.name, 'cyclusci@submit-1.batlab.org:polyphemus/fetch/cyclus.git'])
        fetchfile.close()

        rtn, out = check_cmd(['ssh', 'cyclusci@submit-1.batlab.org', 'cd', 'polyphemus;', 'nmi_submit', 'cyclus.run-spec'])
        lines = out.splitlines()
        report_url = lines[-1].strip()
        print(report_url)
