"""This provides simple file listing for pages which are different in the 
original and pull request.  The file listings are links which take the user
to the 3-way diff page as rendered by the `polyphemus.swcpage` plugin.

This module is available as an polyphemus plugin by the name `polyphemus.swcpages`.

Software Carpentry File Listing API
===================================
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

    route = '/<ghowner>/<ghrepo>/<int:pr>'

    request_methods = ['GET']

    def response(self, rc, ghowner, ghrepo, pr):
        resp = ""
        event = None
        orp = (ghowner, ghrepo, pr)
        cache = PersistentCache(cachefile=rc.swc_cache)
        pages = cache[ghowner, ghrepo, pr]['files'] if orp in cache else []
        pages.sort()
        resp = render_template("swcpages.html", rc=rc, request=request, 
                ghowner=ghowner, ghrepo=ghrepo, pr=pr, pages=pages)
        return resp, event
