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
kallithea.model.notification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Model for notifications


This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 20, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

from pylons import tmpl_context as c
from pylons.i18n.translation import _

import kallithea
from kallithea.lib import helpers as h
from kallithea.model import BaseModel
from kallithea.model.db import Notification, User, UserNotification
from kallithea.model.meta import Session

log = logging.getLogger(__name__)


class NotificationModel(BaseModel):

    cls = Notification

    def __get_notification(self, notification):
        if isinstance(notification, Notification):
            return notification
        elif isinstance(notification, (int, long)):
            return Notification.get(notification)
        else:
            if notification:
                raise Exception('notification must be int, long or Instance'
                                ' of Notification got %s' % type(notification))

    def create(self, created_by, subject, body, recipients=None,
               type_=Notification.TYPE_MESSAGE, with_email=True,
               email_kwargs={}):
        """

        Creates notification of given type

        :param created_by: int, str or User instance. User who created this
            notification
        :param subject:
        :param body:
        :param recipients: list of int, str or User objects, when None
            is given send to all admins
        :param type_: type of notification
        :param with_email: send email with this notification
        :param email_kwargs: additional dict to pass as args to email template
        """
        from kallithea.lib.celerylib import tasks, run_task

        if recipients and not getattr(recipients, '__iter__', False):
            raise Exception('recipients must be a list or iterable')

        created_by_obj = self._get_user(created_by)

        recipients_objs = []
        if recipients:
            for u in recipients:
                obj = self._get_user(u)
                if obj:
                    recipients_objs.append(obj)
                else:
                    # TODO: inform user that requested operation couldn't be completed
                    log.error('cannot email unknown user %r', u)
            recipients_objs = set(recipients_objs)
            log.debug('sending notifications %s to %s' % (
                type_, recipients_objs)
            )
        elif recipients is None:
            # empty recipients means to all admins
            recipients_objs = User.query().filter(User.admin == True).all()
            log.debug('sending notifications %s to admins: %s' % (
                type_, recipients_objs)
            )
        #else: silently skip notification mails?

        # TODO: inform user who are notified
        notif = Notification.create(
            created_by=created_by_obj, subject=subject,
            body=body, recipients=recipients_objs, type_=type_
        )

        if not with_email:
            return notif

        #don't send email to person who created this comment
        rec_objs = set(recipients_objs).difference(set([created_by_obj]))

        headers = None
        if 'threading' in email_kwargs:
            headers = {'References': ' '.join('<%s>' % x for x in email_kwargs['threading'])}

        # send email with notification to all other participants
        for rec in rec_objs:
            email_body = None  # we set body to none, we just send HTML emails
            ## this is passed into template
            kwargs = {'subject': subject,
                      'body': h.rst_w_mentions(body),
                      'when': h.fmt_date(notif.created_on),
                      'user': notif.created_by_user.username,
                      }

            kwargs.update(email_kwargs)
            email_subject = EmailNotificationModel()\
                                .get_email_description(type_, **kwargs)
            email_body_html = EmailNotificationModel()\
                                .get_email_tmpl(type_, **kwargs)

            run_task(tasks.send_email, [rec.email], email_subject, email_body,
                     email_body_html, headers)

        return notif

    def delete(self, user, notification):
        # we don't want to remove actual notification just the assignment
        try:
            notification = self.__get_notification(notification)
            user = self._get_user(user)
            if notification and user:
                obj = UserNotification.query()\
                        .filter(UserNotification.user == user)\
                        .filter(UserNotification.notification
                                == notification)\
                        .one()
                Session().delete(obj)
                return True
        except Exception:
            log.error(traceback.format_exc())
            raise

    def get_for_user(self, user, filter_=None):
        """
        Get notifications for given user, filter them if filter dict is given

        :param user:
        :param filter:
        """
        user = self._get_user(user)

        q = UserNotification.query()\
            .filter(UserNotification.user == user)\
            .join((Notification, UserNotification.notification_id ==
                                 Notification.notification_id))

        if filter_:
            q = q.filter(Notification.type_.in_(filter_))

        return q.all()

    def mark_read(self, user, notification):
        try:
            notification = self.__get_notification(notification)
            user = self._get_user(user)
            if notification and user:
                obj = UserNotification.query()\
                        .filter(UserNotification.user == user)\
                        .filter(UserNotification.notification
                                == notification)\
                        .one()
                obj.read = True
                Session().add(obj)
                return True
        except Exception:
            log.error(traceback.format_exc())
            raise

    def mark_all_read_for_user(self, user, filter_=None):
        user = self._get_user(user)
        q = UserNotification.query()\
            .filter(UserNotification.user == user)\
            .filter(UserNotification.read == False)\
            .join((Notification, UserNotification.notification_id ==
                                 Notification.notification_id))
        if filter_:
            q = q.filter(Notification.type_.in_(filter_))

        # this is a little inefficient but sqlalchemy doesn't support
        # update on joined tables :(
        for obj in q.all():
            obj.read = True
            Session().add(obj)

    def get_unread_cnt_for_user(self, user):
        user = self._get_user(user)
        return UserNotification.query()\
                .filter(UserNotification.read == False)\
                .filter(UserNotification.user == user).count()

    def get_unread_for_user(self, user):
        user = self._get_user(user)
        return [x.notification for x in UserNotification.query()\
                .filter(UserNotification.read == False)\
                .filter(UserNotification.user == user).all()]

    def get_user_notification(self, user, notification):
        user = self._get_user(user)
        notification = self.__get_notification(notification)

        return UserNotification.query()\
            .filter(UserNotification.notification == notification)\
            .filter(UserNotification.user == user).scalar()

    def make_description(self, notification, show_age=True):
        """
        Creates a human readable description based on properties
        of notification object
        """
        #alias
        _n = notification
        _map = {
            _n.TYPE_CHANGESET_COMMENT: _('%(user)s commented on changeset at %(when)s'),
            _n.TYPE_MESSAGE: _('%(user)s sent message at %(when)s'),
            _n.TYPE_MENTION: _('%(user)s mentioned you at %(when)s'),
            _n.TYPE_REGISTRATION: _('%(user)s registered in Kallithea at %(when)s'),
            _n.TYPE_PULL_REQUEST: _('%(user)s opened new pull request at %(when)s'),
            _n.TYPE_PULL_REQUEST_COMMENT: _('%(user)s commented on pull request at %(when)s')
        }
        tmpl = _map[notification.type_]

        if show_age:
            when = h.age(notification.created_on)
        else:
            when = h.fmt_date(notification.created_on)

        return tmpl % dict(
            user=notification.created_by_user.username,
            when=when,
            )


class EmailNotificationModel(BaseModel):

    TYPE_CHANGESET_COMMENT = Notification.TYPE_CHANGESET_COMMENT
    TYPE_MESSAGE = Notification.TYPE_MESSAGE # only used for testing
    # Notification.TYPE_MENTION is not used
    TYPE_PASSWORD_RESET = 'password_link'
    TYPE_REGISTRATION = Notification.TYPE_REGISTRATION
    TYPE_PULL_REQUEST = Notification.TYPE_PULL_REQUEST
    TYPE_PULL_REQUEST_COMMENT = Notification.TYPE_PULL_REQUEST_COMMENT
    TYPE_DEFAULT = 'default'

    def __init__(self):
        super(EmailNotificationModel, self).__init__()
        self._template_root = kallithea.CONFIG['pylons.paths']['templates'][0]
        self._tmpl_lookup = kallithea.CONFIG['pylons.app_globals'].mako_lookup
        self.email_types = {
            self.TYPE_CHANGESET_COMMENT: 'email_templates/changeset_comment.html',
            self.TYPE_PASSWORD_RESET: 'email_templates/password_reset.html',
            self.TYPE_REGISTRATION: 'email_templates/registration.html',
            self.TYPE_DEFAULT: 'email_templates/default.html',
            self.TYPE_PULL_REQUEST: 'email_templates/pull_request.html',
            self.TYPE_PULL_REQUEST_COMMENT: 'email_templates/pull_request_comment.html',
        }
        self._subj_map = {
            self.TYPE_CHANGESET_COMMENT: _('Comment on %(repo_name)s changeset %(short_id)s on %(branch)s by %(comment_username)s'),
            self.TYPE_MESSAGE: 'Test Message',
            # self.TYPE_PASSWORD_RESET
            self.TYPE_REGISTRATION: _('New user %(new_username)s registered'),
            # self.TYPE_DEFAULT
            self.TYPE_PULL_REQUEST: _('Review request on %(repo_name)s pull request #%(pr_id)s from %(ref)s by %(pr_username)s'),
            self.TYPE_PULL_REQUEST_COMMENT: _('Comment on %(repo_name)s pull request #%(pr_id)s from %(ref)s by %(comment_username)s'),
        }

    def get_email_description(self, type_, **kwargs):
        """
        return subject for email based on given type
        """
        tmpl = self._subj_map[type_]
        try:
            subj = tmpl % kwargs
        except KeyError, e:
            log.error('error generating email subject for %r from %s: %s', type_, ','.join(self._subj_map.keys()), e)
            raise
        l = [str(x) for x in [kwargs.get('status_change'), kwargs.get('closing_pr') and _('Closing')] if x]
        if l:
            subj += ' (%s)' % (', '.join(l))
        return subj

    def get_email_tmpl(self, type_, **kwargs):
        """
        return generated template for email based on given type
        """

        base = self.email_types.get(type_, self.email_types[self.TYPE_DEFAULT])
        email_template = self._tmpl_lookup.get_template(base)
        # translator and helpers inject
        _kwargs = {'_': _,
                   'h': h,
                   'c': c}
        _kwargs.update(kwargs)
        log.debug('rendering tmpl %s with kwargs %s' % (base, _kwargs))
        return email_template.render(**_kwargs)
