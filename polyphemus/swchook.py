"""The plug in to run on batlab.

This module is available as an polyphemus plugin by the name ``polyphemus.swchook``.

SWC Hook API
============
"""
from __future__ import print_function
import os
import shutil
import sys
import subprocess

try:
    import simplejson as json
except ImportError:
    import json

import github3

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor

if sys.version_info[0] >= 3:
    basestring = str

clone_template = """git clone {url} {dir}"""

checkout_template = """git checkout {commit}"""

rem_add_template = """git remote add {branch} {url}"""

fetch_template = """git fetch {branch}"""

merge_template = """git merge {branch}/{commit}"""

html_diff_template = """htmldiff {file1} {file2}"""

build_html = """make clean; make cache; make check;"""

def clone_repo(url, dir):
    subprocess.check_call(clone_template.format(url=url, dir=dir).split(), 
                          cwd=os.getcwd(), shell=(os.name == 'nt'))
    
def checkout_commit(commit, cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    subprocess.check_call(checkout_template.format(commit=commit).split(), 
                          cwd=cwd, shell=(os.name == 'nt'))

def merge_commit(merge_ref, rem_branch, rem_url, cwd=None):    
    if cwd is None:
        cwd = os.getcwd()
    subprocess.check_call(rem_add_template.format(branch=rem_branch, 
                                                  url=rem_url).split(), 
                          cwd=cwd, shell=(os.name == 'nt'))
    subprocess.check_call(fetch_template.format(branch=rem_branch).split(), 
                          cwd=cwd, shell=(os.name == 'nt'))
    subprocess.check_call(merge_template.format(branch=rem_branch, 
                                                commit=merge_ref).split(), 
                          cwd=cwd, shell=(os.name == 'nt'))
        
class PolyphemusPlugin(Plugin):
    """This class provides functionality for comparing SWC website PRs."""

    requires = ('polyphemus.swcbase',)

    def __init__(self):
        self._files = []
        self._home_dir = os.path.abspath(os.getcwd())

    def _build_base_html(self, base):
        base_repo = github3.repository(*base.repo)

        if os.path.exists(self._base_dir):
            shutil.rmtree(self._base_dir)
        
        clone_repo(base_repo.clone_url, self._base_dir)
        checkout_commit(base.ref, cwd=self._base_dir)
        subprocess.check_call(build_html, cwd=self._base_dir, shell=True)

    def _build_head_html(self, base, head):        
        head_repo = github3.repository(*head.repo)
        base_repo = github3.repository(*base.repo)

        if os.path.exists(self._head_dir):
            shutil.rmtree(self._head_dir)
                
        clone_repo(head_repo.clone_url, self._head_dir)
        checkout_commit(head.ref, cwd=self._head_dir)
        merge_commit(base.ref, "upstream", base_repo.clone_url, 
                     cwd=self._head_dir)
        subprocess.check_call(build_html, shell=True, 
                              cwd=self._head_dir)

    def _generate_diffs(self):
        if os.path.exists(self._diff_dir):
            shutil.rmtree(self._diff_dir)

        for f in self._files:
            fpath, fname = os.path.split(f)
            d = os.path.join(self._diff_dir, fpath)
            os.makedirs(d)

            head = os.path.join(self._head_dir, f)
            base = os.path.join(self._base_dir, f)
            diff = os.path.join(self._diff_dir, f)

            diff_txt = subprocess.check_output(
                html_diff_template.format(file1=base, 
                                          file2=head).split(), 
                shell=(os.name == 'nt'))

            with open(diff, 'w') as f:
                f.write(diff_txt)

    def _dump_state(self):
        with open('swc_state.json', 'w') as outfile:
            json.dumps({'base': self._base_dir, 
                        'head': self._head_dir, 
                        'diff': self._diff_dir,
                        'files': self._files},
                       outfile, indent=4, separators=(',', ': '))
                    
    def execute(self, rc):
        event_name = rc.event.name
        pr = rc.event.data  # pull request object

        event = rc.event = Event(name='swc-status', data={'status': 'error', 
                                 'number': pr.number, 'description': ''})
        
        if not pr.mergeable:
            event.data['description'] = "Error, PR #{0} is not mergeable.".format(pr.number)
            return 
        
        self._files = [os.path.join(*f.filename.split("/")) for f in pr.iter_files()]

        self._base_dir = os.path.join(self._home_dir, str(pr.number), "base")
        self._head_dir = os.path.join(self._home_dir, str(pr.number), "head")
        self._diff_dir = os.path.join(self._home_dir, str(pr.number), "diff")
                  
        self._build_head_html(pr.base, pr.head)
        self._build_base_html(pr.base)
        self._generate_diffs()
        self._dump_state()
