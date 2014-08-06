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
kallithea.controllers.branches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

branches controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 21, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import binascii

from pylons import tmpl_context as c

from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.compat import OrderedDict
from kallithea.lib.utils2 import safe_unicode

log = logging.getLogger(__name__)


class BranchesController(BaseRepoController):

    def __before__(self):
        super(BranchesController, self).__before__()

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def index(self):

        def _branchtags(localrepo):
            bt_closed = {}
            for bn, heads in localrepo.branchmap().iteritems():
                tip = heads[-1]
                if 'close' in localrepo.changelog.read(tip)[5]:
                    bt_closed[bn] = tip
            return bt_closed

        cs_g = c.db_repo_scm_instance.get_changeset

        c.repo_closed_branches = {}
        if c.db_repo.repo_type == 'hg':
            bt_closed = _branchtags(c.db_repo_scm_instance._repo)
            _closed_branches = [(safe_unicode(n), cs_g(binascii.hexlify(h)),)
                                for n, h in bt_closed.items()]

            c.repo_closed_branches = OrderedDict(sorted(_closed_branches,
                                                    key=lambda ctx: ctx[0],
                                                    reverse=False))

        _branches = [(safe_unicode(n), cs_g(h))
                     for n, h in c.db_repo_scm_instance.branches.items()]
        c.repo_branches = OrderedDict(sorted(_branches,
                                             key=lambda ctx: ctx[0],
                                             reverse=False))

        return render('branches/branches.html')
