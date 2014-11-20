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
kallithea.controllers.home
~~~~~~~~~~~~~~~~~~~~~~~~~~

Home controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Feb 18, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""

import logging

from pylons import tmpl_context as c, request
from pylons.i18n.translation import _
from webob.exc import HTTPBadRequest
from sqlalchemy.sql.expression import func

from kallithea.lib.utils import jsonify, conditional_cache
from kallithea.lib.compat import json
from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from kallithea.lib.base import BaseController, render
from kallithea.model.db import Repository, RepoGroup
from kallithea.model.repo import RepoModel


log = logging.getLogger(__name__)


class HomeController(BaseController):

    def __before__(self):
        super(HomeController, self).__before__()

    def about(self):
        return render('/about.html')

    @LoginRequired()
    def index(self):
        c.groups = self.scm_model.get_repo_groups()
        c.group = None

        c.repos_list = Repository.query()\
                        .filter(Repository.group_id == None)\
                        .order_by(func.lower(Repository.repo_name))\
                        .all()

        repos_data = RepoModel().get_repos_as_dict(repos_list=c.repos_list,
                                                   admin=False)
        #json used to render the grid
        c.data = json.dumps(repos_data)

        return render('/index.html')

    @LoginRequired()
    @jsonify
    def repo_switcher_data(self):
        #wrapper for conditional cache
        def _c():
            log.debug('generating switcher repo/groups list')
            all_repos = Repository.query().order_by(Repository.repo_name).all()
            repo_iter = self.scm_model.get_repos(all_repos, simple=True)
            all_groups = RepoGroup.query().order_by(RepoGroup.group_name).all()
            repo_groups_iter = self.scm_model.get_repo_groups(all_groups)

            res = [{
                    'text': _('Groups'),
                    'children': [
                       {'id': obj.group_name, 'text': obj.group_name,
                        'type': 'group', 'obj': {}} for obj in repo_groups_iter]
                   }, {
                    'text': _('Repositories'),
                    'children': [
                       {'id': obj['name'], 'text': obj['name'],
                        'type': 'repo', 'obj': obj['dbrepo']} for obj in repo_iter]
                   }]

            data = {
                'more': False,
                'results': res
            }
            return data

        if request.is_xhr:
            condition = False
            compute = conditional_cache('short_term', 'cache_desc',
                                        condition=condition, func=_c)
            return compute()
        else:
            raise HTTPBadRequest()

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def branch_tag_switcher(self, repo_name):
        if request.is_xhr:
            c.db_repo = Repository.get_by_repo_name(repo_name)
            if c.db_repo:
                c.db_repo_scm_instance = c.db_repo.scm_instance
                return render('/switch_to_list.html')
        raise HTTPBadRequest()

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def repo_refs_data(self, repo_name):
        repo = Repository.get_by_repo_name(repo_name).scm_instance
        res = []
        _branches = repo.branches.items()
        if _branches:
            res.append({
                'text': _('Branch'),
                'children': [{'id': rev, 'text': name, 'type': 'branch'} for name, rev in _branches]
            })
        _tags = repo.tags.items()
        if _tags:
            res.append({
                'text': _('Tag'),
                'children': [{'id': rev, 'text': name, 'type': 'tag'} for name, rev in _tags]
            })
        _bookmarks = repo.bookmarks.items()
        if _bookmarks:
            res.append({
                'text': _('Bookmark'),
                'children': [{'id': rev, 'text': name, 'type': 'book'} for name, rev in _bookmarks]
            })
        data = {
            'more': False,
            'results': res
        }
        return data
