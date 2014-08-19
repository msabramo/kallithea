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
kallithea.controllers.pullrequests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pull requests controller for Kallithea for initializing pull requests

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 7, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback
import formencode
import re

from webob.exc import HTTPNotFound, HTTPForbidden, HTTPBadRequest

from pylons import request, tmpl_context as c, url
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

from kallithea.lib.compat import json
from kallithea.lib.base import BaseRepoController, render
from kallithea.lib.auth import LoginRequired, HasRepoPermissionAnyDecorator,\
    NotAnonymous
from kallithea.lib.helpers import Page
from kallithea.lib import helpers as h
from kallithea.lib import diffs
from kallithea.lib.utils import action_logger, jsonify
from kallithea.lib.vcs.utils import safe_str
from kallithea.lib.vcs.exceptions import EmptyRepositoryError
from kallithea.lib.diffs import LimitedDiffContainer
from kallithea.model.db import  PullRequest, ChangesetStatus, ChangesetComment,\
    PullRequestReviewers
from kallithea.model.pull_request import PullRequestModel
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.comment import ChangesetCommentsModel
from kallithea.model.changeset_status import ChangesetStatusModel
from kallithea.model.forms import PullRequestForm, PullRequestPostForm
from kallithea.lib.utils2 import safe_int
from kallithea.controllers.changeset import _ignorews_url,\
    _context_url, get_line_ctx, get_ignore_ws
from kallithea.controllers.compare import CompareController
from kallithea.lib.graphmod import graph_data

log = logging.getLogger(__name__)


class PullrequestsController(BaseRepoController):

    def __before__(self):
        super(PullrequestsController, self).__before__()
        repo_model = RepoModel()
        c.users_array = repo_model.get_users_js()
        c.user_groups_array = repo_model.get_user_groups_js()

    def _get_repo_refs(self, repo, rev=None, branch=None, branch_rev=None):
        """return a structure with repo's interesting changesets, suitable for
        the selectors in pullrequest.html

        rev: a revision that must be in the list somehow and selected by default
        branch: a branch that must be in the list and selected by default - even if closed
        branch_rev: a revision of which peers should be preferred and available."""
        # list named branches that has been merged to this named branch - it should probably merge back
        peers = []

        if rev:
            rev = safe_str(rev)

        if branch:
            branch = safe_str(branch)

        if branch_rev:
            branch_rev = safe_str(branch_rev)
            # a revset not restricting to merge() would be better
            # (especially because it would get the branch point)
            # ... but is currently too expensive
            # including branches of children could be nice too
            peerbranches = set()
            for i in repo._repo.revs(
                "sort(parents(branch(id(%s)) and merge()) - branch(id(%s)), -rev)",
                branch_rev, branch_rev):
                abranch = repo.get_changeset(i).branch
                if abranch not in peerbranches:
                    n = 'branch:%s:%s' % (abranch, repo.get_changeset(abranch).raw_id)
                    peers.append((n, abranch))
                    peerbranches.add(abranch)

        selected = None
        tiprev = repo.tags.get('tip')
        tipbranch = None

        branches = []
        for abranch, branchrev in repo.branches.iteritems():
            n = 'branch:%s:%s' % (abranch, branchrev)
            desc = abranch
            if branchrev == tiprev:
                tipbranch = abranch
                desc = '%s (current tip)' % desc
            branches.append((n, desc))
            if rev == branchrev:
                selected = n
            if branch == abranch:
                if not rev:
                    selected = n
                branch = None
        if branch:  # branch not in list - it is probably closed
            branchrev = repo.closed_branches.get(branch)
            if branchrev:
                n = 'branch:%s:%s' % (branch, branchrev)
                branches.append((n, _('%s (closed)') % branch))
                selected = n
                branch = None
            if branch:
                log.error('branch %r not found in %s', branch, repo)

        bookmarks = []
        for bookmark, bookmarkrev in repo.bookmarks.iteritems():
            n = 'book:%s:%s' % (bookmark, bookmarkrev)
            bookmarks.append((n, bookmark))
            if rev == bookmarkrev:
                selected = n

        tags = []
        for tag, tagrev in repo.tags.iteritems():
            if tag == 'tip':
                continue
            n = 'tag:%s:%s' % (tag, tagrev)
            tags.append((n, tag))
            if rev == tagrev:
                selected = n

        # prio 1: rev was selected as existing entry above

        # prio 2: create special entry for rev; rev _must_ be used
        specials = []
        if rev and selected is None:
            selected = 'rev:%s:%s' % (rev, rev)
            specials = [(selected, '%s: %s' % (_("Changeset"), rev[:12]))]

        # prio 3: most recent peer branch
        if peers and not selected:
            selected = peers[0][0]

        # prio 4: tip revision
        if not selected:
            if h.is_hg(repo):
                if tipbranch:
                    selected = 'branch:%s:%s' % (tipbranch, tiprev)
                else:
                    selected = 'tag:null:0'
                    tags.append((selected, 'null'))
            else:
                if 'master' in repo.branches:
                    selected = 'branch:master:%s' % repo.branches['master']
                else:
                    k, v = repo.branches.items()[0]
                    selected = 'branch:%s:%s' % (k, v)

        groups = [(specials, _("Special")),
                  (peers, _("Peer branches")),
                  (bookmarks, _("Bookmarks")),
                  (branches, _("Branches")),
                  (tags, _("Tags")),
                  ]
        return [g for g in groups if g[0]], selected

    def _get_is_allowed_change_status(self, pull_request):
        if pull_request.is_closed():
            return False

        owner = self.authuser.user_id == pull_request.user_id
        reviewer = self.authuser.user_id in [x.user_id for x in
                                                   pull_request.reviewers]
        return self.authuser.admin or owner or reviewer

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def show_all(self, repo_name):
        c.from_ = request.GET.get('from_') or ''
        c.closed = request.GET.get('closed') or ''
        c.pull_requests = PullRequestModel().get_all(repo_name, from_=c.from_, closed=c.closed)
        c.repo_name = repo_name
        p = safe_int(request.GET.get('page', 1), 1)

        c.pullrequests_pager = Page(c.pull_requests, page=p, items_per_page=10)

        c.pullrequest_data = render('/pullrequests/pullrequest_data.html')

        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            return c.pullrequest_data

        return render('/pullrequests/pullrequest_show_all.html')

    @LoginRequired()
    def show_my(self): # my_account_my_pullrequests
        c.show_closed = request.GET.get('pr_show_closed')
        return render('/pullrequests/pullrequest_show_my.html')

    @NotAnonymous()
    def show_my_data(self):
        c.show_closed = request.GET.get('pr_show_closed')

        def _filter(pr):
            s = sorted(pr, key=lambda o: o.created_on, reverse=True)
            if not c.show_closed:
                s = filter(lambda p: p.status != PullRequest.STATUS_CLOSED, s)
            return s

        c.my_pull_requests = _filter(PullRequest.query()\
                                .filter(PullRequest.user_id ==
                                        self.authuser.user_id)\
                                .all())

        c.participate_in_pull_requests = _filter(PullRequest.query()\
                                .join(PullRequestReviewers)\
                                .filter(PullRequestReviewers.user_id ==
                                        self.authuser.user_id)\
                                                 )

        return render('/pullrequests/pullrequest_show_my_data.html')

    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def index(self):
        org_repo = c.db_repo
        org_scm_instance = org_repo.scm_instance
        try:
            org_scm_instance.get_changeset()
        except EmptyRepositoryError, e:
            h.flash(h.literal(_('There are no changesets yet')),
                    category='warning')
            redirect(url('summary_home', repo_name=org_repo.repo_name))

        org_rev = request.GET.get('rev_end')
        # rev_start is not directly useful - its parent could however be used
        # as default for other and thus give a simple compare view
        #other_rev = request.POST.get('rev_start')
        branch = request.GET.get('branch')

        c.cs_repos = [(org_repo.repo_name, org_repo.repo_name)]
        c.default_cs_repo = org_repo.repo_name
        c.cs_refs, c.default_cs_ref = self._get_repo_refs(org_scm_instance, rev=org_rev, branch=branch)

        # add org repo to other so we can open pull request against peer branches on itself
        c.a_repos = [(org_repo.repo_name, '%s (self)' % org_repo.repo_name)]

        # add parent of this fork also and select it
        if org_repo.parent:
            c.a_repos.append((org_repo.parent.repo_name, '%s (parent)' % org_repo.parent.repo_name))
            c.a_repo = org_repo.parent
            c.a_refs, c.default_a_ref = self._get_repo_refs(org_repo.parent.scm_instance)
        else:
            c.a_repo = org_repo
            c.a_refs, c.default_a_ref = self._get_repo_refs(org_scm_instance) # without rev and branch

        # gather forks and add to this list ... even though it is rare to
        # request forks to pull from their parent
        for fork in org_repo.forks:
            c.a_repos.append((fork.repo_name, fork.repo_name))

        return render('/pullrequests/pullrequest.html')

    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def repo_info(self, repo_name):
        repo = RepoModel()._get_repo(repo_name)
        refs, selected_ref = self._get_repo_refs(repo.scm_instance)
        return {
            'description': repo.description.split('\n', 1)[0],
            'selected_ref': selected_ref,
            'refs': refs,
            'user': dict(user_id=repo.user.user_id,
                         username=repo.user.username,
                         firstname=repo.user.firstname,
                         lastname=repo.user.lastname,
                         gravatar_link=h.gravatar_url(repo.user.email, 14)),
            }

    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def create(self, repo_name):
        repo = RepoModel()._get_repo(repo_name)
        try:
            _form = PullRequestForm(repo.repo_id)().to_python(request.POST)
        except formencode.Invalid, errors:
            log.error(traceback.format_exc())
            log.error(str(errors))
            msg = _('Error creating pull request: %s') % errors.msg
            h.flash(msg, 'error')
            raise HTTPBadRequest

        # heads up: org and other might seem backward here ...
        org_repo_name = _form['org_repo']
        org_ref = _form['org_ref'] # will have merge_rev as rev but symbolic name
        org_repo = RepoModel()._get_repo(org_repo_name)
        (org_ref_type,
         org_ref_name,
         org_rev) = org_ref.split(':')

        other_repo_name = _form['other_repo']
        other_ref = _form['other_ref'] # will have symbolic name and head revision
        other_repo = RepoModel()._get_repo(other_repo_name)
        (other_ref_type,
         other_ref_name,
         other_rev) = other_ref.split(':')

        cs_ranges, _cs_ranges_not, ancestor_rev = \
            CompareController._get_changesets(org_repo.scm_instance.alias,
                                              other_repo.scm_instance, other_rev, # org and other "swapped"
                                              org_repo.scm_instance, org_rev,
                                              )
        revisions = [cs.raw_id for cs in cs_ranges]

        # hack: ancestor_rev is not an other_rev but we want to show the
        # requested destination and have the exact ancestor
        other_ref = '%s:%s:%s' % (other_ref_type, other_ref_name, ancestor_rev)

        reviewers = _form['review_members']

        title = _form['pullrequest_title']
        if not title:
            title = '%s#%s to %s#%s' % (org_repo_name, h.short_ref(org_ref_type, org_ref_name),
                                        other_repo_name, h.short_ref(other_ref_type, other_ref_name))
        description = _form['pullrequest_desc'].strip() or _('No description')
        try:
            pull_request = PullRequestModel().create(
                self.authuser.user_id, org_repo_name, org_ref, other_repo_name,
                other_ref, revisions, reviewers, title, description
            )
            Session().commit()
            h.flash(_('Successfully opened new pull request'),
                    category='success')
        except Exception:
            h.flash(_('Error occurred while creating pull request'),
                    category='error')
            log.error(traceback.format_exc())
            return redirect(url('pullrequest_home', repo_name=repo_name))

        return redirect(pull_request.url())

    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def copy_update(self, repo_name, pull_request_id):
        old_pull_request = PullRequest.get_or_404(pull_request_id)
        assert old_pull_request.other_repo.repo_name == repo_name
        if old_pull_request.is_closed():
            raise HTTPForbidden()

        org_repo = RepoModel()._get_repo(old_pull_request.org_repo.repo_name)
        org_ref_type, org_ref_name, org_rev = old_pull_request.org_ref.split(':')
        updaterev = request.POST.get('updaterev')
        if updaterev:
            new_org_rev = self._get_ref_rev(org_repo, 'rev', updaterev)
        else:
            # assert org_ref_type == 'branch', org_ref_type # TODO: what if not?
            new_org_rev = self._get_ref_rev(org_repo, org_ref_type, org_ref_name)

        other_repo = RepoModel()._get_repo(old_pull_request.other_repo.repo_name)
        other_ref_type, other_ref_name, other_rev = old_pull_request.other_ref.split(':') # other_rev is ancestor
        #assert other_ref_type == 'branch', other_ref_type # TODO: what if not?
        new_other_rev = self._get_ref_rev(other_repo, other_ref_type, other_ref_name)

        cs_ranges, _cs_ranges_not, ancestor_rev = CompareController._get_changesets(org_repo.scm_instance.alias,
            other_repo.scm_instance, new_other_rev, # org and other "swapped"
            org_repo.scm_instance, new_org_rev)

        old_revisions = set(old_pull_request.revisions)
        revisions = [cs.raw_id for cs in cs_ranges]
        new_revisions = [r for r in revisions if r not in old_revisions]
        lost = old_revisions.difference(revisions)

        infos = ['','', 'This is an update of %s "%s".' %
                 (h.canonical_url('pullrequest_show', repo_name=old_pull_request.other_repo.repo_name,
                      pull_request_id=pull_request_id),
                  old_pull_request.title)]

        if lost:
            infos.append(_('Missing changesets since the previous version:'))
            for r in old_pull_request.revisions:
                if r in lost:
                    desc = org_repo.get_changeset(r).message.split('\n')[0]
                    infos.append('  %s "%s"' % (h.short_id(r), desc))

        if new_revisions:
            infos.append(_('New changesets on %s %s since the previous version:') % (org_ref_type, org_ref_name))
            for r in reversed(revisions):
                if r in new_revisions:
                    desc = org_repo.get_changeset(r).message.split('\n')[0]
                    infos.append('  %s %s' % (h.short_id(r), h.shorter(desc, 80)))

            if ancestor_rev == other_rev:
                infos.append(_("Ancestor didn't change - show diff since previous version:"))
                infos.append(h.canonical_url('compare_url',
                                 repo_name=org_repo.repo_name, # other_repo is always same as repo_name
                                 org_ref_type='rev', org_ref_name=h.short_id(org_rev), # use old org_rev as base
                                 other_ref_type='rev', other_ref_name=h.short_id(new_org_rev),
                                 )) # note: linear diff, merge or not doesn't matter
            else:
                infos.append(_('This pull request is based on another %s revision and there is no simple diff.') % other_ref_name)
        else:
           infos.append(_('No changes found on %s %s since previous version.') % (org_ref_type, org_ref_name))
           # TODO: fail?

        # hack: ancestor_rev is not an other_ref but we want to show the
        # requested destination and have the exact ancestor
        new_other_ref = '%s:%s:%s' % (other_ref_type, other_ref_name, ancestor_rev)
        new_org_ref = '%s:%s:%s' % (org_ref_type, org_ref_name, new_org_rev)

        reviewers = [r.user_id for r in old_pull_request.reviewers]
        try:
            old_title, old_v = re.match(r'(.*)\(v(\d+)\)\s*$', old_pull_request.title).groups()
            v = int(old_v) + 1
        except (AttributeError, ValueError):
            old_title = old_pull_request.title
            v = 2
        title = '%s (v%s)' % (old_title.strip(), v)
        description = (old_pull_request.description.rstrip() +
                       '\n'.join(infos))

        try:
            pull_request = PullRequestModel().create(
                self.authuser.user_id,
                old_pull_request.org_repo.repo_name, new_org_ref,
                old_pull_request.other_repo.repo_name, new_other_ref,
                revisions, reviewers, title, description
            )
        except Exception:
            h.flash(_('Error occurred while creating pull request'),
                    category='error')
            log.error(traceback.format_exc())
            return redirect(old_pull_request.url())

        ChangesetCommentsModel().create(
            text=_('Closed, replaced by %s .') % h.canonical_url('pullrequest_show',
                                                   repo_name=old_pull_request.other_repo.repo_name,
                                                   pull_request_id=pull_request.pull_request_id),
            repo=old_pull_request.other_repo.repo_id,
            user=c.authuser.user_id,
            pull_request=pull_request_id,
            closing_pr=True)
        PullRequestModel().close_pull_request(pull_request_id)

        Session().commit()
        h.flash(_('Pull request update created'),
                category='success')

        return redirect(pull_request.url())

    # pullrequest_post for PR editing
    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def post(self, repo_name, pull_request_id):
        repo = RepoModel()._get_repo(repo_name)
        pull_request = PullRequest.get_or_404(pull_request_id)
        old_description = pull_request.description

        _form = PullRequestPostForm()().to_python(request.POST)

        pull_request.title = _form['pullrequest_title']
        pull_request.description = _form['pullrequest_desc'].strip() or _('No description')

        PullRequestModel().mention_from_description(pull_request, old_description)

        Session().commit()
        h.flash(_('Pull request updated'), category='success')

        return redirect(pull_request.url())

    # pullrequest_update for updating reviewer list
    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def update(self, repo_name, pull_request_id):
        pull_request = PullRequest.get_or_404(pull_request_id)
        if pull_request.is_closed():
            raise HTTPForbidden()
        #only owner or admin can update it
        owner = pull_request.author.user_id == c.authuser.user_id
        repo_admin = h.HasRepoPermissionAny('repository.admin')(c.repo_name)
        if h.HasPermissionAny('hg.admin') or repo_admin or owner:
            reviewers_ids = map(int, filter(lambda v: v not in [None, ''],
                request.POST.get('reviewers_ids', '').split(',')))

            PullRequestModel().update_reviewers(pull_request_id, reviewers_ids)
            Session().commit()
            return True
        raise HTTPForbidden()

    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def delete(self, repo_name, pull_request_id):
        pull_request = PullRequest.get_or_404(pull_request_id)
        #only owner can delete it !
        if pull_request.author.user_id == c.authuser.user_id:
            PullRequestModel().delete(pull_request)
            Session().commit()
            h.flash(_('Successfully deleted pull request'),
                    category='success')
            return redirect(url('my_pullrequests'))
        raise HTTPForbidden()

    @LoginRequired()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    def show(self, repo_name, pull_request_id, extra=None):
        repo_model = RepoModel()
        c.users_array = repo_model.get_users_js()
        c.user_groups_array = repo_model.get_user_groups_js()
        c.pull_request = PullRequest.get_or_404(pull_request_id)
        c.allowed_to_change_status = self._get_is_allowed_change_status(c.pull_request)
        cc_model = ChangesetCommentsModel()
        cs_model = ChangesetStatusModel()

        # pull_requests repo_name we opened it against
        # ie. other_repo must match
        if repo_name != c.pull_request.other_repo.repo_name:
            raise HTTPNotFound

        # load compare data into template context
        c.cs_repo = c.pull_request.org_repo
        (c.cs_ref_type,
         c.cs_ref_name,
         c.cs_rev) = c.pull_request.org_ref.split(':')

        c.a_repo = c.pull_request.other_repo
        (c.a_ref_type,
         c.a_ref_name,
         c.a_rev) = c.pull_request.other_ref.split(':') # other_rev is ancestor

        org_scm_instance = c.cs_repo.scm_instance # property with expensive cache invalidation check!!!
        c.cs_repo = c.cs_repo
        c.cs_ranges = [org_scm_instance.get_changeset(x) for x in c.pull_request.revisions]
        c.cs_ranges_org = None # not stored and not important and moving target - could be calculated ...
        revs = [ctx.revision for ctx in reversed(c.cs_ranges)]
        c.jsdata = json.dumps(graph_data(org_scm_instance, revs))

        c.available = []
        c.cs_branch_name = c.cs_ref_name
        other_scm_instance = c.a_repo.scm_instance
        c.update_msg = ""
        c.update_msg_other = ""
        if org_scm_instance.alias == 'hg' and c.a_ref_name != 'ancestor':
            if c.cs_ref_type != 'branch':
                c.cs_branch_name = org_scm_instance.get_changeset(c.cs_ref_name).branch # use ref_type ?
            other_branch_name = c.a_ref_name
            if c.a_ref_type != 'branch':
                other_branch_name = other_scm_instance.get_changeset(c.a_ref_name).branch # use ref_type ?
            # candidates: descendants of old head that are on the right branch
            #             and not are the old head itself ...
            #             and nothing at all if old head is a descendent of target ref name
            if other_scm_instance._repo.revs('present(%s)::&%s', c.cs_ranges[-1].raw_id, other_branch_name):
                c.update_msg = _('This pull request has already been merged to %s.') % other_branch_name
            else: # look for children of PR head on source branch in org repo
                arevs = org_scm_instance._repo.revs('%s:: & branch(%s) - %s',
                                                    revs[0], c.cs_branch_name, revs[0])
                if arevs:
                    if c.pull_request.is_closed():
                        c.update_msg = _('This pull request has been closed and can not be updated with descendent changes on %s:') % c.cs_branch_name
                    else:
                        c.update_msg = _('This pull request can be updated with descendent changes on %s:') % c.cs_branch_name
                    c.available = [org_scm_instance.get_changeset(x) for x in arevs]
                else:
                    c.update_msg = _('No changesets found for updating this pull request.')

            revs = org_scm_instance._repo.revs('head() & not (%s::) & branch(%s) & !closed()', revs[0], c.cs_branch_name)
            if revs:
                c.update_msg_other = _('Note: Branch %s also contains unrelated changes, such as %s.') % (c.cs_branch_name,
                    h.short_id(org_scm_instance.get_changeset((max(revs))).raw_id))
            else:
                c.update_msg_other = _('Branch %s does not contain other changes.') % c.cs_branch_name
        elif org_scm_instance.alias == 'git':
            c.update_msg = _("Git pull requests don't support updates yet.")

        raw_ids = [x.raw_id for x in c.cs_ranges]
        c.cs_comments = c.cs_repo.get_comments(raw_ids)
        c.statuses = c.cs_repo.statuses(raw_ids)

        ignore_whitespace = request.GET.get('ignorews') == '1'
        line_context = request.GET.get('context', 3)
        c.ignorews_url = _ignorews_url
        c.context_url = _context_url
        c.fulldiff = request.GET.get('fulldiff')
        diff_limit = self.cut_off_limit if not c.fulldiff else None

        # we swap org/other ref since we run a simple diff on one repo
        log.debug('running diff between %s and %s in %s'
                  % (c.a_rev, c.cs_rev, org_scm_instance.path))
        txtdiff = org_scm_instance.get_diff(rev1=safe_str(c.a_rev), rev2=safe_str(c.cs_rev),
                                      ignore_whitespace=ignore_whitespace,
                                      context=line_context)

        diff_processor = diffs.DiffProcessor(txtdiff or '', format='gitdiff',
                                             diff_limit=diff_limit)
        _parsed = diff_processor.prepare()

        c.limited_diff = False
        if isinstance(_parsed, LimitedDiffContainer):
            c.limited_diff = True

        c.files = []
        c.changes = {}
        c.lines_added = 0
        c.lines_deleted = 0

        for f in _parsed:
            st = f['stats']
            c.lines_added += st['added']
            c.lines_deleted += st['deleted']
            fid = h.FID('', f['filename'])
            c.files.append([fid, f['operation'], f['filename'], f['stats']])
            htmldiff = diff_processor.as_html(enable_comments=True,
                                              parsed_lines=[f])
            c.changes[fid] = [f['operation'], f['filename'], htmldiff]

        # inline comments
        c.inline_cnt = 0
        c.inline_comments = cc_model.get_inline_comments(
                                c.db_repo.repo_id,
                                pull_request=pull_request_id)
        # count inline comments
        for __, lines in c.inline_comments:
            for comments in lines.values():
                c.inline_cnt += len(comments)
        # comments
        c.comments = cc_model.get_comments(c.db_repo.repo_id,
                                           pull_request=pull_request_id)

        # (badly named) pull-request status calculation based on reviewer votes
        (c.pull_request_reviewers,
         c.pull_request_pending_reviewers,
         c.current_voting_result,
         ) = cs_model.calculate_pull_request_result(c.pull_request)
        c.changeset_statuses = ChangesetStatus.STATUSES

        c.as_form = False
        c.ancestor = None # there is one - but right here we don't know which
        return render('/pullrequests/pullrequest_show.html')

    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def comment(self, repo_name, pull_request_id):
        pull_request = PullRequest.get_or_404(pull_request_id)

        status = 0
        close_pr = False
        allowed_to_change_status = self._get_is_allowed_change_status(pull_request)
        if allowed_to_change_status:
            status = request.POST.get('changeset_status')
            close_pr = request.POST.get('save_close')
        text = request.POST.get('text', '').strip() or _('No comments.')
        if close_pr:
            text = _('Closing.') + '\n' + text

        comm = ChangesetCommentsModel().create(
            text=text,
            repo=c.db_repo.repo_id,
            user=c.authuser.user_id,
            pull_request=pull_request_id,
            f_path=request.POST.get('f_path'),
            line_no=request.POST.get('line'),
            status_change=(ChangesetStatus.get_status_lbl(status)
                           if status and allowed_to_change_status else None),
            closing_pr=close_pr
        )

        action_logger(self.authuser,
                      'user_commented_pull_request:%s' % pull_request_id,
                      c.db_repo, self.ip_addr, self.sa)

        if allowed_to_change_status:
            # get status if set !
            if status:
                ChangesetStatusModel().set_status(
                    c.db_repo.repo_id,
                    status,
                    c.authuser.user_id,
                    comm,
                    pull_request=pull_request_id
                )

            if close_pr:
                PullRequestModel().close_pull_request(pull_request_id)
                action_logger(self.authuser,
                              'user_closed_pull_request:%s' % pull_request_id,
                              c.db_repo, self.ip_addr, self.sa)

        Session().commit()

        if not request.environ.get('HTTP_X_PARTIAL_XHR'):
            return redirect(pull_request.url())

        data = {
           'target_id': h.safeid(h.safe_unicode(request.POST.get('f_path'))),
        }
        if comm:
            c.co = comm
            data.update(comm.get_dict())
            data.update({'rendered_text':
                         render('changeset/changeset_comment_block.html')})

        return data

    @LoginRequired()
    @NotAnonymous()
    @HasRepoPermissionAnyDecorator('repository.read', 'repository.write',
                                   'repository.admin')
    @jsonify
    def delete_comment(self, repo_name, comment_id):
        co = ChangesetComment.get(comment_id)
        if co.pull_request.is_closed():
            #don't allow deleting comments on closed pull request
            raise HTTPForbidden()

        owner = co.author.user_id == c.authuser.user_id
        repo_admin = h.HasRepoPermissionAny('repository.admin')(c.repo_name)
        if h.HasPermissionAny('hg.admin') or repo_admin or owner:
            ChangesetCommentsModel().delete(comment=co)
            Session().commit()
            return True
        else:
            raise HTTPForbidden()
