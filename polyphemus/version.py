"""Version information about polyphemus and its dependencies.
"""

import re
from collections import namedtuple

class version_info(namedtuple('version_info', ['major', 'minor', 'micro', 'extra'])):
    """A representation of version information.
    """
    def __new__(cls, major=-1, minor=-1, micro=-1, extra=''):
        return super(version_info, cls).__new__(cls, major, minor, micro, extra)

_ver_r = re.compile('(\d+)\.(\d+)\.?(\d+)?[-_ \.]*?(.*)')

def version_parser(ver):
    """Parses a nominal version string into a version_info object.
    e.g. '0.20dev' -> version_info(0, 20, 0, 'dev').
    """
    m = _ver_r.match(ver)
    g = m.groups()
    vi = version_info(int(g[0]), int(g[1] or 0), int(g[2] or 0), g[3])
    return vi

def report_versions():
    """Creates a string that reports the version of polyphemus and all its
    dependencies.
    """
    vstr = ("Polyphemus: {polyphemus_version}\n"
            )
    return vstr.format(**globals())

#
# Polyphemus
#

polyphemus_version = '0.1'
polyphemus_version_info = version_info(0, 1, 0, '')

