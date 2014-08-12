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
kallithea.model.pull_request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pull request model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jun 6, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import datetime

from pylons.i18n.translation import _

from kallithea.model.meta import Session
from kallithea.lib import helpers as h
from kallithea.model import BaseModel
from kallithea.model.db import PullRequest, PullRequestReviewers, Notification,\
    ChangesetStatus, User
from kallithea.model.notification import NotificationModel
from kallithea.lib.utils2 import extract_mentioned_users, safe_unicode


log = logging.getLogger(__name__)


class PullRequestModel(BaseModel):

    cls = PullRequest

    def __get_pull_request(self, pull_request):
        return self._get_instance(PullRequest, pull_request)

    def get_pullrequest_cnt_for_user(self, user):
        return PullRequest.query()\
                                .join(PullRequestReviewers)\
                                .filter(PullRequestReviewers.user_id == user)\
                                .filter(PullRequest.status != PullRequest.STATUS_CLOSED)\
                                .count()

    def get_all(self, repo_name, from_=False, closed=False):
        """Get all PRs for repo.
        Default is all PRs to the repo, PRs from the repo if from_.
        Closed PRs are only included if closed is true."""
        repo = self._get_repo(repo_name)
        q = PullRequest.query()
        if from_:
            q = q.filter(PullRequest.org_repo == repo)
        else:
            q = q.filter(PullRequest.other_repo == repo)
        if not closed:
            q = q.filter(PullRequest.status != PullRequest.STATUS_CLOSED)
        return q.order_by(PullRequest.created_on.desc()).all()

    def create(self, created_by, org_repo, org_ref, other_repo, other_ref,
               revisions, reviewers, title, description=None):
        from kallithea.model.changeset_status import ChangesetStatusModel

        created_by_user = self._get_user(created_by)
        org_repo = self._get_repo(org_repo)
        other_repo = self._get_repo(other_repo)

        new = PullRequest()
        new.org_repo = org_repo
        new.org_ref = org_ref
        new.other_repo = other_repo
        new.other_ref = other_ref
        new.revisions = revisions
        new.title = title
        new.description = description
        new.author = created_by_user
        Session().add(new)
        Session().flush()

        #reset state to under-review
        from kallithea.model.comment import ChangesetCommentsModel
        comment = ChangesetCommentsModel().create(
            text=u'Auto status change to %s' % (ChangesetStatus.get_status_lbl(ChangesetStatus.STATUS_UNDER_REVIEW)),
            repo=org_repo,
            user=new.author,
            pull_request=new,
            send_email=False
        )
        ChangesetStatusModel().set_status(
            org_repo,
            ChangesetStatus.STATUS_UNDER_REVIEW,
            new.author,
            comment,
            pull_request=new
        )

        mention_recipients = set(User.get_by_username(username, case_insensitive=True)
                                 for username in extract_mentioned_users(new.description))
        self.__add_reviewers(new, reviewers, mention_recipients)

        return new

    def __add_reviewers(self, pr, reviewers, mention_recipients=None):
        #members
        for member in set(reviewers):
            _usr = self._get_user(member)
            reviewer = PullRequestReviewers(_usr, pr)
            Session().add(reviewer)

        revision_data = [(x.raw_id, x.message)
                         for x in map(pr.org_repo.get_changeset, pr.revisions)]

        #notification to reviewers
        pr_url = pr.url(canonical=True)
        threading = [h.canonical_url('pullrequest_show', repo_name=pr.other_repo.repo_name,
                                     pull_request_id=pr.pull_request_id)]
        subject = safe_unicode(
            h.link_to(
              _('%(user)s wants you to review pull request #%(pr_id)s: %(pr_title)s') % \
                {'user': pr.author.username,
                 'pr_title': pr.title,
                 'pr_id': pr.pull_request_id},
                pr_url)
            )
        body = pr.description
        _org_ref_type, org_ref_name, _org_rev = pr.org_ref.split(':')
        email_kwargs = {
            'pr_title': pr.title,
            'pr_user_created': h.person(pr.author),
            'pr_repo_url': h.canonical_url('summary_home', repo_name=pr.other_repo.repo_name),
            'pr_url': pr_url,
            'pr_revisions': revision_data,
            'repo_name': pr.other_repo.repo_name,
            'pr_id': pr.pull_request_id,
            'ref': org_ref_name,
            'pr_username': pr.author.username,
            'threading': threading,
            'is_mention': False,
            }
        if reviewers:
            NotificationModel().create(created_by=pr.author, subject=subject, body=body,
                                       recipients=reviewers,
                                       type_=Notification.TYPE_PULL_REQUEST,
                                       email_kwargs=email_kwargs)

        if mention_recipients:
            mention_recipients.discard(None)
            mention_recipients.difference_update(reviewers)
        if mention_recipients:
            email_kwargs['is_mention'] = True
            subject = _('[Mention]') + ' ' + subject

            NotificationModel().create(created_by=pr.author, subject=subject, body=body,
                                       recipients=mention_recipients,
                                       type_=Notification.TYPE_PULL_REQUEST,
                                       email_kwargs=email_kwargs)

    def mention_from_description(self, pr, old_description=''):
        mention_recipients = set(User.get_by_username(username, case_insensitive=True)
                                 for username in extract_mentioned_users(pr.description))
        mention_recipients.difference_update(User.get_by_username(username, case_insensitive=True)
                                             for username in extract_mentioned_users(old_description))

        log.debug("Mentioning %s" % mention_recipients)
        self.__add_reviewers(pr, [], mention_recipients)

    def update_reviewers(self, pull_request, reviewers_ids):
        reviewers_ids = set(reviewers_ids)
        pull_request = self.__get_pull_request(pull_request)
        current_reviewers = PullRequestReviewers.query()\
                            .filter(PullRequestReviewers.pull_request==
                                   pull_request)\
                            .all()
        current_reviewers_ids = set([x.user.user_id for x in current_reviewers])

        to_add = reviewers_ids.difference(current_reviewers_ids)
        to_remove = current_reviewers_ids.difference(reviewers_ids)

        log.debug("Adding %s reviewers" % to_add)
        self.__add_reviewers(pull_request, to_add)

        log.debug("Removing %s reviewers" % to_remove)
        for uid in to_remove:
            reviewer = PullRequestReviewers.query()\
                    .filter(PullRequestReviewers.user_id==uid,
                            PullRequestReviewers.pull_request==pull_request)\
                    .scalar()
            if reviewer:
                Session().delete(reviewer)

    def delete(self, pull_request):
        pull_request = self.__get_pull_request(pull_request)
        Session().delete(pull_request)

    def close_pull_request(self, pull_request):
        pull_request = self.__get_pull_request(pull_request)
        pull_request.status = PullRequest.STATUS_CLOSED
        pull_request.updated_on = datetime.datetime.now()
        Session().add(pull_request)
