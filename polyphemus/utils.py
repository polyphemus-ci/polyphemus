"""Helpers for polyphemus.

Utilities API
=============
"""
from __future__ import print_function
import os
import io
import re
import sys
import glob
import tempfile
import functools
import subprocess
from copy import deepcopy
from pprint import pformat
from collections import Mapping, Iterable, Hashable, Sequence, namedtuple, \
    MutableMapping
from hashlib import md5
from warnings import warn
try:
    import cPickle as pickle
except ImportError:
    import pickle

if sys.version_info[0] >= 3:
    basestring = str

DEFAULT_RC_FILE = "polyphemusrc.py"
"""Default run control file name."""

DEFAULT_PLUGINS = ('polyphemus.base', 'polyphemus.githubhook', 'polyphemus.batlabrun', 
                   'polyphemus.batlabstat', 'polyphemus.githubstat', 
                   'polyphemus.dashboard')
"""Default list of plugin module names."""

FORBIDDEN_NAMES = frozenset(['del', 'global'])

def warn_forbidden_name(forname, inname=None, rename=None):
    """Warns the user that a forbidden name has been found."""
    msg = "found forbidden name {0!r}".format(forname)
    if inname is not None:
        msg += " in {0!r}".format(inname)
    if rename is not None:
        msg += ", renaming to {0!r}".format(rename)
    warn(msg, RuntimeWarning)

def indent(s, n=4, join=True):
    """Indents all lines in the string or list s by n spaces."""
    spaces = " " * n
    lines = s.splitlines() if isinstance(s, basestring) else s
    lines = lines or ()
    if join:
        return '\n'.join([spaces + l for l in lines if l is not None])
    else:
        return [spaces + l for l in lines if l is not None]


class indentstr(str):
    """A special string subclass that can be used to indent the whol string
    inside of format strings by accessing an ``indentN`` attr.  For example,
    ``s.indent8`` will return a copy of the string s where every line starts
    with 8 spaces."""
    def __getattr__(self, key):
        if key.startswith('indent'):
            return indent(self, n=int(key[6:]))
        return getattr(super(indentstr, self), key)


def expand_default_args(methods):
    """This function takes a collection of method tuples and expands all of
    the default arguments, returning a set of all methods possible."""
    methitems = set()
    for mkey, mrtn in methods:
        mname, margs = mkey[0], mkey[1:]
        havedefaults = [3 == len(arg) for arg in margs]
        if any(havedefaults):
            # expand default arguments
            n = havedefaults.index(True)
            items = [((mname,)+tuple(margs[:n]), mrtn)] + \
                    [((mname,)+tuple(margs[:i]), mrtn) for i in range(n+1,len(margs)+1)]
            methitems.update(items)
        else:
            # no default args
            methitems.add((mkey, mrtn))
    return methitems


def newoverwrite(s, filename, verbose=False):
    """Useful for not forcing re-compiles and thus playing nicely with the
    build system.  This is acomplished by not writing the file if the existsing
    contents are exactly the same as what would be written out.

    Parameters
    ----------
    s : str
        string contents of file to possible
    filename : str
        Path to file.
    vebose : bool, optional
        prints extra message

    """
    if os.path.isfile(filename):
        with io.open(filename, 'rb') as f:
            old = f.read()
        if s == old:
            return
    else:
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
    with io.open(filename, 'wb') as f:
        f.write(s.encode())
    if verbose:
        print("  wrote " + filename)

def newcopyover(f1, f2, verbose=False):
    """Useful for not forcing re-compiles and thus playing nicely with the
    build system.  This is acomplished by not writing the file if the existsing
    contents are exactly the same as what would be written out.

    Parameters
    ----------
    f1 : str
        Path to file to copy from
    f2 : str
        Path to file to copy over
    vebose : bool, optional
        prints extra message

    """
    if os.path.isfile(f1):
        with io.open(f1, 'r') as f:
            s = f.read()
        return newoverwrite(s, f2, verbose)

def writenewonly(s, filename, verbose=False):
    """Only writes the contents of the string to a file if the file does not exist.
    Useful for not tocuhing files.

    Parameters
    ----------
    s : str
        string contents of file to possible
    filename : str
        Path to file.
    vebose : bool, optional
        prints extra message

    """
    if os.path.isfile(filename):
        return
    with open(filename, 'w') as f:
        f.write(str(s))
    if verbose:
        print("  wrote " + filename)

def ensuredirs(f):
    """For a file path, ensure that its directory path exists."""
    d = os.path.split(f)[0]
    if not os.path.isdir(d):
        os.makedirs(d)

def touch(filename):
    """Opens a file and updates the mtime, like the posix command of the same name."""
    with io.open(filename, 'a') as f:
        os.utime(filename, None)


def exec_file(filename, glb=None, loc=None):
    """A function equivalent to the Python 2.x execfile statement."""
    with io.open(filename, 'r') as f:
        src = f.read()
    exec(compile(src, filename, "exec"), glb, loc)

#
# Run Control
#

class NotSpecified(object):
    """A helper class singleton for run control meaning that a 'real' value
    has not been given."""
    def __repr__(self):
        return "NotSpecified"

NotSpecified = NotSpecified()
"""A helper class singleton for run control meaning that a 'real' value
has not been given."""

class RunControl(object):
    """A composable configuration class. Unlike argparse.Namespace,
    this keeps the object dictionary (__dict__) separate from the run 
    control attributes dictionary (_dict)."""

    def __init__(self, **kwargs):
        """Parameters
        -------------
        kwargs : optional
            Items to place into run control.

        """
        self._dict = {}
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._updaters = {}

    def __getattr__(self, key):
        if key in self._dict:
            return self._dict[key]
        elif key in self.__dict__:
            return self.__dict__[key]
        elif key in self.__class__.__dict__:
            return self.__class__.__dict__[key]
        else:
            msg = "RunControl object has no attribute {0!r}.".format(key)
            raise AttributeError(msg)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            self.__dict__[key] = value
        else:
            if value is NotSpecified and key in self:
                return
            self._dict[key] = value

    def __delattr__(self, key):
        if key in self._dict:
            del self._dict[key]
        elif key in self.__dict__:
            del self.__dict__[key]
        elif key in self.__class__.__dict__:
            del self.__class__.__dict__[key]
        else:
            msg = "RunControl object has no attribute {0!r}.".format(key)
            raise AttributeError(msg)

    def __iter__(self):
        return iter(self._dict)

    def __repr__(self):
        keys = sorted(self._dict.keys())
        s = ", ".join(["{0!s}={1!r}".format(k, self._dict[k]) for k in keys])
        return "{0}({1})".format(self.__class__.__name__, s)

    def _pformat(self):
        keys = sorted(self._dict.keys())
        f = lambda k: "{0!s}={1}".format(k, pformat(self._dict[k], indent=2))
        s = ",\n ".join(map(f, keys))
        return "{0}({1})".format(self.__class__.__name__, s)

    def __contains__(self, key):
        return key in self._dict or key in self.__dict__ or \
                                    key in self.__class__.__dict__

    def __eq__(self, other):
        if hasattr(other, '_dict'):
            return self._dict == other._dict
        elif isinstance(other, Mapping):
            return self._dict == other
        else:
            return NotImplemented

    def __ne__(self, other):
        if hasattr(other, '_dict'):
            return self._dict != other._dict
        elif isinstance(other, Mapping):
            return self._dict != other
        else:
            return NotImplemented

    def _update(self, other):
        """Updates the rc with values from another mapping.  If this rc has
        if a key is in self, other, and self._updaters, then the updaters
        value is called to perform the update.  This function should return
        a copy to be safe and not update in-place.
        """
        if hasattr(other, '_dict'):
            other = other._dict
        elif not hasattr(other, 'items'):
            other = dict(other)
        for k, v in other.items():
            if v is NotSpecified:
                pass
            elif k in self._updaters and k in self:
                v = self._updaters[k](getattr(self, k), v)
            setattr(self, k, v)

def infer_format(filename, format):
    """Tries to figure out a file format."""
    if isinstance(format, basestring):
        pass
    elif filename.endswith('.pkl.gz'):
        format = 'pkl.gz'
    elif filename.endswith('.pkl'):
        format = 'pkl'
    else:
        raise ValueError("file format could not be determined.")
    return format

def sortedbytype(iterable):
    """Sorts an iterable by types first, then value."""
    items = {}
    for x in iterable:
        t = type(x).__name__
        if t not in items:
            items[t] = []
        items[t].append(x)
    rtn = []
    for t in sorted(items.keys()):
        rtn.extend(sorted(items[t]))
    return rtn

nyansep = r'~\_/' * 17 + '~=[,,_,,]:3'
"""WAT?!"""

def flatten(iterable):
    """Generator which returns flattened version of nested sequences."""
    for el in iterable:
        if isinstance(el, basestring):
            yield el
        elif isinstance(el, Iterable):
            for subel in flatten(el):
                yield subel
        else:
            yield el

#
# Memoization
#

def ishashable(x):
    """Tests if a value is hashable."""
    if isinstance(x, Hashable):
        if isinstance(x, basestring):
            return True
        elif isinstance(x, Iterable):
            return all(map(ishashable, x))
        else:
         return True
    else:
        return False

def memoize(obj):
    """Generic memoziation decorator based off of code from
    http://wiki.python.org/moin/PythonDecoratorLibrary .
    This is not suitabe for method caching.
    """
    cache = obj.cache = {}
    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        hashable = ishashable(key)
        if hashable:
            if key not in cache:
                cache[key] = obj(*args, **kwargs)
            return cache[key]
        else:
            return obj(*args, **kwargs)
    return memoizer

class memoize_method(object):
    """Decorator suitable for memoizing methods, rather than functions
    and classes.  This is based off of code that may be found at
    http://code.activestate.com/recipes/577452-a-memoize-decorator-for-instance-methods/
    This code was originally released under the MIT license.
    """
    def __init__(self, meth):
        self.meth = meth

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.meth
        p = functools.partial(self, obj)
        p.__doc__ = self.meth.__doc__
        p.__name__ = self.meth.__name__
        return p

    def __call__(self, *args, **kwargs):
        obj = args[0]
        cache = obj._cache = getattr(obj, '_cache', {})
        key = (self.meth, args[1:], tuple(sorted(kwargs.items())))
        hashable = ishashable(key)
        if hashable:
            if key not in cache:
                cache[key] = self.meth(*args, **kwargs)
            return cache[key]
        else:
            return self.meth(*args, **kwargs)

def check_cmd(args):
    """Runs a command in a subprocess and verifies that it executed properly.
    """
    #if not isinstance(args, basestring):
    #    args = " ".join(args)
    f = tempfile.NamedTemporaryFile()
    #rtn = subprocess.call(args, shell=True, stdout=f, stderr=f)
    rtn = subprocess.call(args, stdout=f, stderr=f)
    f.seek(0)
    out = f.read()
    f.close()
    return rtn, out


#
# Persisted Cache
#

class PersistentCache(MutableMapping):
    """A quick persistent cache."""

    def __init__(self, cachefile='cache.pkl'):
        """Parameters
        -------------
        cachefile : str, optional
            Path to description cachefile.

        """
        self.cachefile = cachefile
        if os.path.isfile(cachefile):
            with io.open(cachefile, 'rb') as f:
                self.cache = pickle.load(f)
        else:
            self.cache = {}

    def __len__(self):
        return len(self.cache)

    def __contains__(self, key):
        return key in self.cache

    def __getitem__(self, key):
        return self.cache[key]  # return the results of the finder only

    def __setitem__(self, key, value):
        self.cache[key] = value
        self.dump()

    def __delitem__(self, key):
        del self.cache[key]
        self.dump()

    def __iter__(self):
        for key in self.cache.keys():
            yield key

    def dump(self):
        """Writes the cache out to the filesystem."""
        if not os.path.exists(self.cachefile):
            pardir = os.path.split(os.path.abspath(self.cachefile))[0]
            if not os.path.exists(pardir):
                os.makedirs(pardir)
        with io.open(self.cachefile, 'wb') as f:
            pickle.dump(self.cache, f, pickle.HIGHEST_PROTOCOL)

    def __str__(self):
        return pformat(self.cache)
