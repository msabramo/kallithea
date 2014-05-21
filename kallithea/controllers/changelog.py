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
kallithea.controllers.changelog
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

changelog controller for rhodecode

:created_on: Apr 21, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

from pylons import request, url, session, tmpl_context as c
from pylons.controllers.util import redirect
from pylons.i18n.translation import _
from webob.exc import HTTPNotFound, HTTPBadRequest

import kallithea.lib.helpers as h
from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.helpers import RepoPage
from kallithea.lib.compat import json
from kallithea.lib.graphmod import _colored, _dagwalker
from kallithea.lib.vcs.exceptions import RepositoryError, ChangesetDoesNotExistError,\
    ChangesetError, NodeDoesNotExistError, EmptyRepositoryError
from kallithea.lib.utils2 import safe_int, safe_str


log = logging.getLogger(__name__)


def _load_changelog_summary():
    p = safe_int(request.GET.get('page'), 1)
    size = safe_int(request.GET.get('size'), 10)

    def url_generator(**kw):
        return url('changelog_summary_home',
                   repo_name=c.db_repo.repo_name, size=size, **kw)

    collection = c.db_repo_scm_instance

    c.repo_changesets = RepoPage(collection, page=p,
                                 items_per_page=size,
                                 url=url_generator)
    page_revisions = [x.raw_id for x in list(c.repo_changesets)]
    c.comments = c.db_repo.get_comments(page_revisions)
    c.statuses = c.db_repo.statuses(page_revisions)


class ChangelogController(BaseRepoController):

    def __before__(self):
        super(ChangelogController, self).__before__()
        c.affected_files_cut_off = 60

    def __get_cs_or_redirect(self, rev, repo, redirect_after=True,
                             partial=False):
        """
        Safe way to get changeset if error occur it redirects to changeset with
        proper message. If partial is set then don't do redirect raise Exception
        instead

        :param rev: revision to fetch
        :param repo: repo instance
        """

        try:
            return c.db_repo_scm_instance.get_changeset(rev)
        except EmptyRepositoryError, e:
            if not redirect_after:
                return None
            h.flash(h.literal(_('There are no changesets yet')),
                    category='warning')
            redirect(url('changelog_home', repo_name=repo.repo_name))

        except RepositoryError, e:
            log.error(traceback.format_exc())
            h.flash(safe_str(e), category='warning')
            if not partial:
                redirect(h.url('changelog_home', repo_name=repo.repo_name))
            raise HTTPBadRequest()

    def _graph(self, repo, revs_int, repo_size, size, p):
        """
        Generates a DAG graph for repo

        :param repo:
        :param revs_int:
        :param repo_size:
        :param size:
        :param p:
        """
        if not revs_int:
            c.jsdata = json.dumps([])
            return

        data = []
        revs = revs_int

        dag = _dagwalker(repo, revs, repo.alias)
        dag = _colored(dag)
        for (_id, _type, ctx, vtx, edges) in dag:
            data.append(['', vtx, edges])

        c.jsdata = json.dumps(data)

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def index(self, repo_name, revision=None, f_path=None):
        limit = 100
        default = 20
        if request.GET.get('size'):
            c.size = max(min(safe_int(request.GET.get('size')), limit), 1)
            session['changelog_size'] = c.size
            session.save()
        else:
            c.size = int(session.get('changelog_size', default))
        # min size must be 1
        c.size = max(c.size, 1)
        p = safe_int(request.GET.get('page', 1), 1)
        branch_name = request.GET.get('branch', None)
        if (branch_name and
            branch_name not in c.db_repo_scm_instance.branches and
            branch_name not in c.db_repo_scm_instance.closed_branches and
            not revision):
            return redirect(url('changelog_file_home', repo_name=c.repo_name,
                                    revision=branch_name, f_path=f_path or ''))

        c.changelog_for_path = f_path
        try:

            if f_path:
                log.debug('generating changelog for path %s' % f_path)
                # get the history for the file !
                tip_cs = c.db_repo_scm_instance.get_changeset()
                try:
                    collection = tip_cs.get_file_history(f_path)
                except (NodeDoesNotExistError, ChangesetError):
                    #this node is not present at tip !
                    try:
                        cs = self.__get_cs_or_redirect(revision, repo_name)
                        collection = cs.get_file_history(f_path)
                    except RepositoryError, e:
                        h.flash(safe_str(e), category='warning')
                        redirect(h.url('changelog_home', repo_name=repo_name))
                collection = list(reversed(collection))
            else:
                collection = c.db_repo_scm_instance.get_changesets(start=0,
                                                        branch_name=branch_name)
            c.total_cs = len(collection)

            c.pagination = RepoPage(collection, page=p, item_count=c.total_cs,
                                    items_per_page=c.size, branch=branch_name,)
            collection = list(c.pagination)
            page_revisions = [x.raw_id for x in c.pagination]
            c.comments = c.db_repo.get_comments(page_revisions)
            c.statuses = c.db_repo.statuses(page_revisions)
        except (EmptyRepositoryError), e:
            h.flash(safe_str(e), category='warning')
            return redirect(url('summary_home', repo_name=c.repo_name))
        except (RepositoryError, ChangesetDoesNotExistError, Exception), e:
            log.error(traceback.format_exc())
            h.flash(safe_str(e), category='error')
            return redirect(url('changelog_home', repo_name=c.repo_name))

        c.branch_name = branch_name
        c.branch_filters = [('', _('All Branches'))] + \
            [(k, k) for k in c.db_repo_scm_instance.branches.keys()]
        if c.db_repo_scm_instance.closed_branches:
            prefix = _('(closed)') + ' '
            c.branch_filters += [('-', '-')] + \
                [(k, prefix + k) for k in c.db_repo_scm_instance.closed_branches.keys()]
        _revs = []
        if not f_path:
            _revs = [x.revision for x in c.pagination]
        self._graph(c.db_repo_scm_instance, _revs, c.total_cs, c.size, p)

        return render('changelog/changelog.html')

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def changelog_details(self, cs):
        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            c.cs = c.db_repo_scm_instance.get_changeset(cs)
            return render('changelog/changelog_details.html')
        raise HTTPNotFound()

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def changelog_summary(self, repo_name):
        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            _load_changelog_summary()

            return render('changelog/changelog_summary_data.html')
        raise HTTPNotFound()
