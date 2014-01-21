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

clone_template = """git clone {url} {dir};
cd {dir};
git checkout {commit};"""

merge_template = """git remote add upstream {url};
git fetch upstream;
git merge upstream/{commit};
"""

html_diff_template = """htmldiff {file1} {file2} > {diff};"""

build_html = """make clean;
make cache;
make check;"""

class PolyphemusPlugin(Plugin):
    """This class provides functionality for comparing SWC website PRs."""

    requires = ('polyphemus.swcbase',)

    def __init__(self):
        self._files = []
        self._home_dir = os.getcwd()
        self._base_dir = "base"
        self._head_dir = "head"
        self._diff_dir = "diff"

    def _build_base_html(self, base):
        base_repo = github3.repository(*base.repo)
        cmd = []
        cmd += clone_template.format(url=base_repo.clone_url, 
                                     dir=self._base_dir, commit=base).split()
        cmd += build_html.split()
        cmd += ["cd ", self._home_dir]
        subprocess.check_call(cmd, shell=(os.name == 'nt'))

    def _populate_head_html(self, base, head):        
        head_repo = github3.repository(*head.repo)
        base_repo = github3.repository(*base.repo)

        cmd = []
        cmd += clone_template.format(url=head_repo.clone_url, dir=self._head_dir, 
                                     commit=head.ref).split()
        cmd += merge_template.format(url=base_repo.clone_url, commit=base.ref).split()
        cmd += build_html.split()
        cmd += ["cd ", self._home_dir]
        subprocess.check_call(cmd, shell=(os.name == 'nt'))

    def _generate_diffs(self):
        for f in self_.files:
            fpath = f.split("/")
            d = os.path.join(diff_dir, *fpath[:-1])
            os.makedirs(d)
            head = os.path.join(self._head_dir, fpath)
            base = os.path.join(self._base_dir, fpath)
            diff = os.path.join(self._diff_dir, fpath)
            subprocess.check_call(html_diff_template.format(base, head, diff).split(), shell=(os.name == 'nt'))
                    
    def execute(self, rc):
        event_name = rc.event.name
        pr = rc.event.data  # pull request object

        event = rc.event = Event(name='swc-status', data={'status': 'error', 
                                 'number': pr.number, 'description': ''})
        
        if not pr.mergeable:
            event.data['description'] = "Error, PR is not mergeable."
            return 
        
        self._files = list(pr.iter_files())
                  
        self._populate_head_html(pr.base, pr.head)
        self._build_base_html(pr.base)
        self._generate_diffs()
