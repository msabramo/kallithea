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
kallithea.controllers.bookmarks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bookmarks controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Dec 1, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging

from pylons import tmpl_context as c

from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.compat import OrderedDict
from webob.exc import HTTPNotFound

log = logging.getLogger(__name__)


class BookmarksController(BaseRepoController):

    def __before__(self):
        super(BookmarksController, self).__before__()

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def index(self):
        if c.db_repo_scm_instance.alias != 'hg':
            raise HTTPNotFound()

        c.repo_bookmarks = OrderedDict()

        bookmarks = [(name, c.db_repo_scm_instance.get_changeset(hash_)) for \
                 name, hash_ in c.db_repo_scm_instance._repo._bookmarks.items()]
        ordered_tags = sorted(bookmarks, key=lambda x: x[1].date, reverse=True)
        for name, cs_book in ordered_tags:
            c.repo_bookmarks[name] = cs_book

        return render('bookmarks/bookmarks.html')
