"""The plug in to check SWC website changes.

This module is available as an polyphemus plugin by the name ``polyphemus.swchook``.

SWC Hook API
============
"""
from __future__ import print_function
import os
import re
import sys
import cgi
import shutil
import subprocess
from warnings import warn

import lxml.html
import lxml.etree
from lxml.html.diff import htmldiff, html_annotate

try:
    import simplejson as json
except ImportError:
    import json

import github3

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor
from .githubbase import set_pull_request_status

if sys.version_info[0] >= 3:
    basestring = str

clone_template = """git clone {url} {dir}"""

checkout_template = """git checkout {commit}"""

rem_add_template = """git remote add {branch} {url}"""

fetch_template = """git fetch {branch}"""

merge_template = """git merge {branch}/{commit}"""

build_html = """make clean; make cache; make check;"""

head_re = re.compile('<\s*head\s*>', re.S | re.I)

KNOWN_EXTS = set(['.html', '.htm', '.ipynb'])

ins_del_stylesheet = '''
ins { background-color: #aaffaa; text-decoration: none }
del { background-color: #ff8888; text-decoration: line-through }
'''

def add_stylesheet(elem, ss=ins_del_stylesheet):
    """Adds a stylesheet to the end of an element."""
    s = lxml.etree.Element('style', type="text/css")
    s.text = ss
    elem.append(s)

def clone_repo(url, dir):
    subprocess.check_call(
        clone_template.format(url=url, dir=dir).split(), 
        cwd=os.getcwd(), shell=(os.name == 'nt'))
    
def checkout_commit(commit, cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    subprocess.check_call(
        checkout_template.format(commit=commit).split(), 
        cwd=cwd, shell=(os.name == 'nt'))

def add_fetch_remote(rem_branch, rem_url, cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    subprocess.check_call(
        rem_add_template.format(branch=rem_branch, url=rem_url).split(), 
        cwd=cwd, shell=(os.name == 'nt'))
    subprocess.check_call(
        fetch_template.format(branch=rem_branch).split(), 
        cwd=cwd, shell=(os.name == 'nt'))

def merge_commit(merge_branch, merge_ref, cwd=None):    
    subprocess.check_call(
        merge_template.format(branch=merge_branch, 
                              commit=merge_ref).split(), 
        cwd=cwd, shell=(os.name == 'nt'))
        
class PolyphemusPlugin(Plugin):
    """This class provides functionality for comparing SWC website PRs.
    """

    requires = ('polyphemus.swcbase',)

    defaultrc = RunControl(
        flask_kwargs={'static_folder': os.path.join(os.getcwd(), 'static')}
        )

    def __init__(self):
        self._files = []

    def _build_base_html(self, base):
        base_repo = github3.repository(*base.repo)

        if os.path.exists(self._base_dir):
            shutil.rmtree(self._base_dir)
        
        self._updater.update(
            status='pending', description="Getting base repository.")
        clone_repo(base_repo.clone_url, self._base_dir)
        checkout_commit(base.ref, cwd=self._base_dir)

        self._updater.update(
            status='pending', description="Building base website.")
        subprocess.check_call(build_html, cwd=self._base_dir, shell=True)

    def _build_head_html(self, base, head):        
        head_repo = github3.repository(*head.repo)
        base_repo = github3.repository(*base.repo)

        if os.path.exists(self._head_dir):
            shutil.rmtree(self._head_dir)
                
        self._updater.update(
            status='pending', description="Getting head repository.")
        clone_repo(head_repo.clone_url, self._head_dir)
        add_fetch_remote("upstream", base_repo.clone_url, 
                         cwd=self._head_dir)
        checkout_commit(base.ref, cwd=self._head_dir)
        merge_commit("origin", head.ref, cwd=self._head_dir)

        self._updater.update(
            status='pending', description="Building head website.")
        subprocess.check_call(build_html, shell=True, cwd=self._head_dir)

    def _generate_diffs(self):
        self._updater.update(
            status='pending', 
            description="Creating head and base website diffs.")

        for f in self._files:
            f = os.path.join("_site", f)
            fpath, fname = os.path.split(f)

            head = os.path.join(self._head_dir, f)
            base = os.path.join(self._base_dir, f)
            diff = os.path.join(self._head_dir, fpath, "diff-" + fname)

            # if addition or deletion, just skip
            if not os.path.isfile(head) or not os.path.isfile(base):
                continue

            with open(base, 'r') as f:
                doc1 = lxml.html.parse(f)
 
            with open(head, 'r') as f:
                doc2 = lxml.html.parse(f)
 
            doc1body = doc1.find('body')
            doc2body = doc2.find('body')

            bodydiff = htmldiff(lxml.html.tostring(doc1body).decode(),
                                lxml.html.tostring(doc2body).decode())
            doc2head = doc2.find('head')
            add_stylesheet(doc2head)
            diffdoc = '<html>\n{0}\n<body>\n{1}\n</body>\n</html>'
            diffdoc = diffdoc.format(lxml.html.tostring(doc2head).decode(), bodydiff)

            with open(diff, 'w') as f:
                f.write(diffdoc)
            print("diff'd {0!r}".format(diff))

    @runfor('swc-hook', 'github-pr-new', 'github-pr-sync')                    
    def execute(self, rc):
        event_name = rc.event.name
        pr = rc.event.data  # pull request object

        rc.event = Event(name='swc-status', 
                         data={'status': 'error', 
                               'number': pr.number, 
                               'description': ''})
        self._updater = rc.event.data

        if not pr.mergeable:
            msg = "Error, PR #{0} is not mergeable.".format(pr.number)
            warn(msg, RuntimeWarning)
            rc.event.data['status'] = 'failure'
            self._updater['description'] = msg
            return 
        
        self._files = [os.path.join(*f.filename.split("/")) 
                       for f in pr.iter_files()]
        self._files = [f for f in self._files if os.path.splitext(f)[1] in KNOWN_EXTS]

        orp = (rc.github_owner, rc.github_repo, pr.number)
        stat_dir = rc.flask_kwargs['static_folder']
        orp_dir = "{0}-{1}-{2}".format(*orp)
        stat_orp_dir = os.path.join(stat_dir, orp_dir)
        self._base_dir = os.path.join(stat_orp_dir, "base")
        self._head_dir = os.path.join(stat_orp_dir, "head")
        if os.path.exists(stat_orp_dir):
            shutil.rmtree(stat_orp_dir)

        self._build_head_html(pr.base, pr.head)
        self._build_base_html(pr.base)
        self._generate_diffs()

        cache = PersistentCache(cachefile=rc.swc_cache)
        cache[orp] = {'base': self._base_dir,
                      'head': self._head_dir,
                      'files': self._files}

        self._updater.update(status='success', description="comparison available.", 
                             target_url=os.path.join(rc.server_url, rc.github_owner, 
                                                     rc.github_repo, str(pr.number)))
