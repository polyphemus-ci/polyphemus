"""Top-level polyphemus entry point.  

Polyphemus Comand Line Interface
=================================
The main module is normally run via the command line interface as follows:

.. code-block:: bash

    path/to/proj/ $ polyphemus

This has the following usage::

    path/to/proj/ $ polyphemus -h 


Main API
========
"""
from __future__ import print_function
import os
import io
import sys
import argparse
import warnings
from pprint import pprint, pformat

try:
    import argcomplete
except ImportError:
    argcomplete = None

from .utils import NotSpecified, RunControl, DEFAULT_RC_FILE, DEFAULT_PLUGINS, \
    exec_file

from .plugins import Plugins

if sys.version_info[0] >= 3:
    basestring = str


def setup(**kwargs):
    """Entry point for polyphemus.  Keyword arguments are interptered as 
    run control parameters.
    """
    warnings.simplefilter('default')
    # Preprocess plugin names, which entails preprocessing the rc file
    preparser = argparse.ArgumentParser("Polyphemus-CI", add_help=False)
    preparser.add_argument('--rc', default=NotSpecified, 
                           help="path to run control file")
    preparser.add_argument('--plugins', default=NotSpecified, nargs="+",
                           help="plugins to include")
    preparser.add_argument('--bash-completion', default=True, action='store_true',
                           help="enable bash completion", dest="bash_completion")
    preparser.add_argument('--no-bash-completion', action='store_false',
                           help="disable bash completion", dest="bash_completion")
    prens = preparser.parse_known_args()[0]
    predefaultrc = RunControl(rc=DEFAULT_RC_FILE, plugins=DEFAULT_PLUGINS)
    prerc = RunControl()
    prerc._update(predefaultrc)
    prerc.rc = prens.rc
    prerc._update(kwargs)
    rcdict = {}
    if os.path.isfile(prerc.rc):
        exec_file(prerc.rc, rcdict, rcdict)
        prerc.rc = rcdict['rc'] if 'rc' in rcdict else NotSpecified
        prerc.plugins = rcdict['plugins'] if 'plugins' in rcdict else NotSpecified
    prerc._update([(k, v) for k, v in prens.__dict__.items()])    

    # run plugins
    plugins = Plugins(prerc.plugins)
    parser = plugins.build_cli()
    if argcomplete is not None and prerc.bash_completion:
        argcomplete.autocomplete(parser)
    ns = parser.parse_args()
    rc = plugins.merge_rcs()
    rc._update(rcdict)
    rc._update([(k, v) for k, v in ns.__dict__.items()])
    plugins.setup()
    plugins.build_app()
    return plugins

def main():
    plugins = setup()
    plugins.run_app()
    plugins.teardown()

if __name__ == '__main__':
    main()
