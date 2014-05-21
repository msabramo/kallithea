# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
kallithea.__init__
~~~~~~~~~~~~~~~~~~

RhodeCode, a web based repository management based on pylons
versioning implementation: http://www.python.org/dev/peps/pep-0386/

:created_on: Apr 9, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH.
:license: GPLv3, see LICENSE.md for more details.
"""

import sys
import platform

VERSION = (2, 2, 5)
BACKENDS = {
    'hg': 'Mercurial repository',
    'git': 'Git repository',
}

CELERY_ON = False
CELERY_EAGER = False

# link to config for pylons
CONFIG = {}

# Linked module for extensions
EXTENSIONS = {}

try:
    from kallithea.lib import get_current_revision
    _rev = get_current_revision(quiet=True)
    if _rev and len(VERSION) > 3:
        VERSION += ('%s' % _rev[0],)
except ImportError:
    pass

__version__ = ('.'.join((str(each) for each in VERSION[:3])))
__dbversion__ = 31  # defines current db version for migrations
__platform__ = platform.system()
__license__ = 'GPLv3'
__py_version__ = sys.version_info
__author__ = 'RhodeCode GmbH'
__url__ = 'https://kallithea-scm.org/'

is_windows = __platform__ in ['Windows']
is_unix = not is_windows

if len(VERSION) > 3:
    __version__ += '.'+VERSION[3]

    if len(VERSION) > 4:
        __version__ += VERSION[4]
    else:
        __version__ += '0'
