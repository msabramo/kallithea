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
kallithea.lib
~~~~~~~~~~~~~

Kallithea libs

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Oct 06, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import os

def get_current_revision(quiet=False):
    """
    Returns tuple of (number, id) from repository containing this package
    or None if repository could not be found.

    :param quiet: prints error for fetching revision if True
    """

    try:
        from kallithea.lib.vcs import get_repo
        from kallithea.lib.vcs.utils.helpers import get_scm
        repopath = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                '..', '..'))
        scm = get_scm(repopath)[0]
        repo = get_repo(path=repopath, alias=scm)
        wk_dir = repo.workdir
        cur_rev = wk_dir.get_changeset()
        return (cur_rev.revision, cur_rev.short_id)
    except Exception, err:
        if not quiet:
            print ("WARNING: Cannot retrieve kallithea's revision. "
                   "disregard this if you don't know what that means. "
                   "Original error was: %s" % err)
        return None
