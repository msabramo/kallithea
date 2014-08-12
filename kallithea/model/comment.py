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
kallithea.model.comment
~~~~~~~~~~~~~~~~~~~~~~~

comments model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 11, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging

from pylons.i18n.translation import _
from sqlalchemy.util.compat import defaultdict

from kallithea.lib.utils2 import extract_mentioned_users, safe_unicode
from kallithea.lib import helpers as h
from kallithea.model import BaseModel
from kallithea.model.db import ChangesetComment, User, \
    Notification, PullRequest
from kallithea.model.notification import NotificationModel
from kallithea.model.meta import Session

log = logging.getLogger(__name__)


class ChangesetCommentsModel(BaseModel):

    cls = ChangesetComment

    def __get_changeset_comment(self, changeset_comment):
        return self._get_instance(ChangesetComment, changeset_comment)

    def __get_pull_request(self, pull_request):
        return self._get_instance(PullRequest, pull_request)

    def _extract_mentions(self, s):
        user_objects = []
        for username in extract_mentioned_users(s):
            user_obj = User.get_by_username(username, case_insensitive=True)
            if user_obj:
                user_objects.append(user_obj)
        return user_objects

    def _get_notification_data(self, repo, comment, user, comment_text,
                               line_no=None, revision=None, pull_request=None,
                               status_change=None, closing_pr=False):
        """
        Get notification data

        :param comment_text:
        :param line:
        :returns: tuple (subj,body,recipients,notification_type,email_kwargs)
        """
        # make notification
        body = comment_text  # text of the comment
        line = ''
        if line_no:
            line = _('on line %s') % line_no

        #changeset
        if revision:
            notification_type = Notification.TYPE_CHANGESET_COMMENT
            cs = repo.scm_instance.get_changeset(revision)
            desc = "%s" % (cs.short_id)

            threading = ['%s-rev-%s@%s' % (repo.repo_name, revision, h.canonical_hostname())]
            if line_no: # TODO: url to file _and_ line number
                threading.append('%s-rev-%s-line-%s@%s' % (repo.repo_name, revision, line_no,
                                                           h.canonical_hostname()))
            comment_url = h.canonical_url('changeset_home',
                repo_name=repo.repo_name,
                revision=revision,
                anchor='comment-%s' % comment.comment_id)
            subj = safe_unicode(
                h.link_to('Re changeset: %(desc)s %(line)s' % \
                          {'desc': desc, 'line': line},
                          comment_url)
            )
            # get the current participants of this changeset
            recipients = ChangesetComment.get_users(revision=revision)
            # add changeset author if it's in kallithea system
            cs_author = User.get_from_cs_author(cs.author)
            if not cs_author:
                #use repo owner if we cannot extract the author correctly
                cs_author = repo.user
            recipients += [cs_author]
            email_kwargs = {
                'status_change': status_change,
                'cs_comment_user': h.person(user),
                'cs_target_repo': h.canonical_url('summary_home', repo_name=repo.repo_name),
                'cs_comment_url': comment_url,
                'raw_id': revision,
                'message': cs.message,
                'repo_name': repo.repo_name,
                'short_id': h.short_id(revision),
                'branch': cs.branch,
                'comment_username': user.username,
                'threading': threading,
            }
        #pull request
        elif pull_request:
            notification_type = Notification.TYPE_PULL_REQUEST_COMMENT
            desc = comment.pull_request.title
            _org_ref_type, org_ref_name, _org_rev = comment.pull_request.org_ref.split(':')
            threading = ['%s-pr-%s@%s' % (pull_request.other_repo.repo_name,
                                          pull_request.pull_request_id,
                                          h.canonical_hostname())]
            if line_no: # TODO: url to file _and_ line number
                threading.append('%s-pr-%s-line-%s@%s' % (pull_request.other_repo.repo_name,
                                                          pull_request.pull_request_id, line_no,
                                                          h.canonical_hostname()))
            comment_url = pull_request.url(canonical=True,
                anchor='comment-%s' % comment.comment_id)
            subj = safe_unicode(
                h.link_to('Re pull request #%(pr_id)s: %(desc)s %(line)s' % \
                          {'desc': desc,
                           'pr_id': comment.pull_request.pull_request_id,
                           'line': line},
                          comment_url)
            )
            # get the current participants of this pull request
            recipients = ChangesetComment.get_users(pull_request_id=
                                                pull_request.pull_request_id)
            # add pull request author
            recipients += [pull_request.author]

            # add the reviewers to notification
            recipients += [x.user for x in pull_request.reviewers]

            #set some variables for email notification
            email_kwargs = {
                'pr_title': pull_request.title,
                'pr_id': pull_request.pull_request_id,
                'status_change': status_change,
                'closing_pr': closing_pr,
                'pr_comment_url': comment_url,
                'pr_comment_user': h.person(user),
                'pr_target_repo': h.canonical_url('summary_home',
                                   repo_name=pull_request.other_repo.repo_name),
                'repo_name': pull_request.other_repo.repo_name,
                'ref': org_ref_name,
                'comment_username': user.username,
                'threading': threading,
            }

        return subj, body, recipients, notification_type, email_kwargs

    def create(self, text, repo, user, revision=None, pull_request=None,
               f_path=None, line_no=None, status_change=None, closing_pr=False,
               send_email=True):
        """
        Creates new comment for changeset or pull request.
        If status_change is not None this comment is associated with a
        status change of changeset or changesets associated with pull request

        :param text:
        :param repo:
        :param user:
        :param revision:
        :param pull_request: (for emails, not for comments)
        :param f_path:
        :param line_no:
        :param status_change: (for emails, not for comments)
        :param closing_pr: (for emails, not for comments)
        :param send_email: also send email
        """
        if not text:
            log.warning('Missing text for comment, skipping...')
            return

        repo = self._get_repo(repo)
        user = self._get_user(user)
        comment = ChangesetComment()
        comment.repo = repo
        comment.author = user
        comment.text = text
        comment.f_path = f_path
        comment.line_no = line_no

        if revision:
            comment.revision = revision
        elif pull_request:
            pull_request = self.__get_pull_request(pull_request)
            comment.pull_request = pull_request
        else:
            raise Exception('Please specify revision or pull_request_id')

        Session().add(comment)
        Session().flush()

        if send_email:
            (subj, body, recipients, notification_type,
             email_kwargs) = self._get_notification_data(
                                repo, comment, user,
                                comment_text=text,
                                line_no=line_no,
                                revision=revision,
                                pull_request=pull_request,
                                status_change=status_change,
                                closing_pr=closing_pr)
            email_kwargs['is_mention'] = False
            # create notification objects, and emails
            NotificationModel().create(
                created_by=user, subject=subj, body=body,
                recipients=recipients, type_=notification_type,
                email_kwargs=email_kwargs,
            )

            mention_recipients = set(self._extract_mentions(body))\
                                    .difference(recipients)
            if mention_recipients:
                email_kwargs['is_mention'] = True
                subj = _('[Mention]') + ' ' + subj
                NotificationModel().create(
                    created_by=user, subject=subj, body=body,
                    recipients=mention_recipients,
                    type_=notification_type,
                    email_kwargs=email_kwargs
                )

        return comment

    def delete(self, comment):
        """
        Deletes given comment

        :param comment_id:
        """
        comment = self.__get_changeset_comment(comment)
        Session().delete(comment)

        return comment

    def get_comments(self, repo_id, revision=None, pull_request=None):
        """
        Gets main comments based on revision or pull_request_id

        :param repo_id:
        :param revision:
        :param pull_request:
        """

        q = ChangesetComment.query()\
                .filter(ChangesetComment.repo_id == repo_id)\
                .filter(ChangesetComment.line_no == None)\
                .filter(ChangesetComment.f_path == None)
        if revision:
            q = q.filter(ChangesetComment.revision == revision)
        elif pull_request:
            pull_request = self.__get_pull_request(pull_request)
            q = q.filter(ChangesetComment.pull_request == pull_request)
        else:
            raise Exception('Please specify revision or pull_request')
        q = q.order_by(ChangesetComment.created_on)
        return q.all()

    def get_inline_comments(self, repo_id, revision=None, pull_request=None):
        q = Session().query(ChangesetComment)\
            .filter(ChangesetComment.repo_id == repo_id)\
            .filter(ChangesetComment.line_no != None)\
            .filter(ChangesetComment.f_path != None)\
            .order_by(ChangesetComment.comment_id.asc())\

        if revision:
            q = q.filter(ChangesetComment.revision == revision)
        elif pull_request:
            pull_request = self.__get_pull_request(pull_request)
            q = q.filter(ChangesetComment.pull_request == pull_request)
        else:
            raise Exception('Please specify revision or pull_request_id')

        comments = q.all()

        paths = defaultdict(lambda: defaultdict(list))

        for co in comments:
            paths[co.f_path][co.line_no].append(co)
        return paths.items()
