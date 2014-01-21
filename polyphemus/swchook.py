"""The plug in to run on batlab.

This module is available as an polyphemus plugin by the name ``polyphemus.swchook``.

SWC Hook API
============
"""
from __future__ import print_function
import os
import sys
import subprocess

import github3

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor

if sys.version_info[0] >= 3:
    basestring = str

clone_template = \
"""
git clone {url} {dir};
cd {dir};
git checkout {commit};"""

merge_template = \
"""
git remote add upstream {url};
git fetch upstream;
git merge upstream/{commit};
"""

cp_template = \
"""
cp {file1} {file2};
"""

html_diff_template = \
"""
htmldiff {file1} {file2} > {diff};
"""

build_html = \
"""
make clean;
make check;"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for comparing SWC website PRs."""

    requires = ('polyphemus.swcbase',)

    def __init__(self):
        _files = []   
        _base_dir = os.getcwd()

    def _cp_html(self, grouping):
        for f in _files:
            path = f.split("/")[:-1]
            fname = f.split("/")[-1]
            htmlpath = os.path.join("_site", *path, fname)
            if os.path.exists(htmlpath):
                comppath = os.path.join(_base_dir, "compare", *path, 
                                        fname.split(".html")[0], 
                                        grouping ".html")
                cp_template.format(file1=htmlpath, file2=compath)

    def _populate_base_html(self, base_repo, sha1):
        cmd = []
        cmd += clone_template.format(url=base_repo.clone_url, dir="base", commit=sha1).split()
        # subprocess.check_call(cmd, shell=(os.name == 'nt'))
        cmd += build_html.split()
        subprocess.check_call(cmd, shell=(os.name == 'nt'))
        _cp_html("base")
        cmd = "rm -r base;".split()
        # subprocess.check_call("rm -r base".split(), shell=(os.name == 'nt'))
        cmd += ["cd ", _base_dir]
        subprocess.check_call(cmd, shell=(os.name == 'nt'))

    def _populate_head_html(self, base_repo, base_sha1, head_repo, head_sha1):
        cmd = []
        cmd += clone_template.format(url=head_repo.clone_url, dir="head", 
                                     commit=head_sha1).split()
        # subprocess.check_call(cmd, shell=(os.name == 'nt'))
        merge_template.format(url=base_repo.clone_url, commit=base_sha1).split()
        # subprocess.check_call(cmd, shell=(os.name == 'nt'))
        cmd += build_html.split()
        subprocess.check_call(cmd, shell=(os.name == 'nt'))
        _cp_html("head")
        cmd = "rm -r head;".split()
        cmd += ["cd ", _base_dir]
        subprocess.check_call(cmd, shell=(os.name == 'nt'))

    def _generate_diffs(self):
        for root, dirs, files in os.walk():
            for dir in dirs:
                if os.path.exists(os.path.join("base.html")) and os.path.exists(os.path.join("head.html")):
                    html_diff_template.format("base.html", "head.html", "diff.html")
                    subprocess.check_call(html_diff_template.split(), shell=(os.name == 'nt'))
        
    def execute(self, rc):
        event_name = rc.event.name
        pr = rc.event.data  # pull request object

        event = rc.event = Event(name='swc-status', data={'status': 'error', 
                                 'number': pr.number, 'description': ''})
        
        if !pr.mergeable:
            event.data['description'] = "Error, PR is not mergeable."
            return 
        
        _files.append(f) for f in pr.iterfiles()
        
        head_repo = github3.repository(*pr.head.repo)
        base_repo = github3.repository(*pr.base.repo)
    
        _populate_base_html(base_repo, pr.base)
        _populate_head_html(head_repo, pr.head)
        _generate_diffs()
