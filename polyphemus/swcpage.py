"""This provides a 3-way diff comparison for rendered HTML pages. The URLs
routed by this extension show the original version of the page, the pull requested 
version of the page, and a visual diff of the two.

This module is available as an polyphemus plugin by the name `polyphemus.swcpage`.

Software Carpentry 3-Way Page Diff API
======================================
"""
from __future__ import print_function
import os
import io
import sys
import pprint
from warnings import warn

if sys.version_info[0] >= 3:
    basestring = str

try:
    import simplejson as json
except ImportError:
    import json

from flask import request, render_template

from .utils import RunControl, NotSpecified, PersistentCache
from .plugins import Plugin
from .event import Event, runfor

class PolyphemusPlugin(Plugin):
    """This class routes the swcpage dashboard."""

    requires = ('polyphemus.swcbase',)

    route = '/<ghowner>/<ghrepo>/<int:pr>/<path:page>'

    request_methods = ['GET']

    def response(self, rc, ghowner, ghrepo, pr, page):
        resp = ""
        event = None

        stat_path = rc.flask_kwargs['static_url_path']  # must start with '/'
        server_url = rc.server_url
        url_prefix = server_url[:-1] + stat_path if server_url.endswith('/') else \
                     server_url + stat_path
        orp_path = "{0}-{1}-{2}/".format(ghowner, ghrepo, pr)
        url_prefix = url_prefix + orp_path if url_prefix.endswith('/') else \
                     url_prefix + '/' + orp_path
        ppath, pname = os.path.split(page)
        base_url = url_prefix + "base/_site/" + page
        head_url = url_prefix + "head/_site/" + page
        diff_url = url_prefix + "head/_site/" + ppath + '/diff-' + pname

        resp = render_template("swcpage.html", rc=rc, request=request, 
                ghowner=ghowner, ghrepo=ghrepo, pr=pr, page=page, base_url=base_url, 
                head_url=head_url, diff_url=diff_url)
        #resp = "No polyphemus dashboard found."
        return resp, event
