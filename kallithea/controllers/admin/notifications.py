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
kallithea.controllers.admin.notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

notifications controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 23, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback

from pylons import request
from pylons import tmpl_context as c
from pylons.controllers.util import abort
from webob.exc import HTTPBadRequest

from kallithea.model.db import Notification
from kallithea.model.notification import NotificationModel
from kallithea.model.meta import Session
from kallithea.lib.auth import LoginRequired, NotAnonymous
from kallithea.lib.base import BaseController, render
from kallithea.lib import helpers as h
from kallithea.lib.helpers import Page
from kallithea.lib.utils2 import safe_int


log = logging.getLogger(__name__)


class NotificationsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""
    # To properly map this controller, ensure your config/routing.py
    # file has a resource setup:
    #     map.resource('notification', 'notifications', controller='_admin/notifications',
    #         path_prefix='/_admin', name_prefix='_admin_')

    @LoginRequired()
    @NotAnonymous()
    def __before__(self):
        super(NotificationsController, self).__before__()

    def index(self, format='html'):
        """GET /_admin/notifications: All items in the collection"""
        # url('notifications')
        c.user = self.authuser
        notif = NotificationModel().get_for_user(self.authuser.user_id,
                                            filter_=request.GET.getall('type'))

        p = safe_int(request.GET.get('page', 1), 1)
        c.notifications = Page(notif, page=p, items_per_page=10)
        c.pull_request_type = Notification.TYPE_PULL_REQUEST
        c.comment_type = [Notification.TYPE_CHANGESET_COMMENT,
                          Notification.TYPE_PULL_REQUEST_COMMENT]

        _current_filter = request.GET.getall('type')
        c.current_filter = 'all'
        if _current_filter == [c.pull_request_type]:
            c.current_filter = 'pull_request'
        elif _current_filter == c.comment_type:
            c.current_filter = 'comment'

        return render('admin/notifications/notifications.html')

    def mark_all_read(self):
        if request.environ.get('HTTP_X_PARTIAL_XHR'):
            nm = NotificationModel()
            # mark all read
            nm.mark_all_read_for_user(self.authuser.user_id,
                                      filter_=request.GET.getall('type'))
            Session().commit()
            c.user = self.authuser
            notif = nm.get_for_user(self.authuser.user_id,
                                    filter_=request.GET.getall('type'))
            c.notifications = Page(notif, page=1, items_per_page=10)
            return render('admin/notifications/notifications_data.html')

    def create(self):
        """POST /_admin/notifications: Create a new item"""
        # url('notifications')

    def new(self, format='html'):
        """GET /_admin/notifications/new: Form to create a new item"""
        # url('new_notification')

    def update(self, notification_id):
        """PUT /_admin/notifications/id: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('notification', notification_id=ID),
        #           method='put')
        # url('notification', notification_id=ID)
        try:
            no = Notification.get(notification_id)
            owner = all(un.user.user_id == c.authuser.user_id
                        for un in no.notifications_to_users)
            if h.HasPermissionAny('hg.admin')() or owner:
                # deletes only notification2user
                NotificationModel().mark_read(c.authuser.user_id, no)
                Session().commit()
                return 'ok'
        except Exception:
            Session().rollback()
            log.error(traceback.format_exc())
        raise HTTPBadRequest()

    def delete(self, notification_id):
        """DELETE /_admin/notifications/id: Delete an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="DELETE" />
        # Or using helpers:
        #    h.form(url('notification', notification_id=ID),
        #           method='delete')
        # url('notification', notification_id=ID)
        try:
            no = Notification.get(notification_id)
            owner = any(un.user.user_id == c.authuser.user_id
                        for un in no.notifications_to_users)
            if h.HasPermissionAny('hg.admin')() or owner:
                # deletes only notification2user
                NotificationModel().delete(c.authuser.user_id, no)
                Session().commit()
                return 'ok'
        except Exception:
            Session().rollback()
            log.error(traceback.format_exc())
        raise HTTPBadRequest()

    def show(self, notification_id, format='html'):
        """GET /_admin/notifications/id: Show a specific item"""
        # url('notification', notification_id=ID)
        c.user = self.authuser
        no = Notification.get(notification_id)

        owner = any(un.user.user_id == c.authuser.user_id
                    for un in no.notifications_to_users)
        repo_admin = h.HasRepoPermissionAny('repository.admin')
        if no and (h.HasPermissionAny('hg.admin')() or repo_admin or owner):
            unotification = NotificationModel()\
                            .get_user_notification(c.user.user_id, no)

            # if this association to user is not valid, we don't want to show
            # this message
            if unotification:
                if not unotification.read:
                    unotification.mark_as_read()
                    Session().commit()
                c.notification = no

                return render('admin/notifications/show_notification.html')

        return abort(403)

    def edit(self, notification_id, format='html'):
        """GET /_admin/notifications/id/edit: Form to edit an existing item"""
        # url('edit_notification', notification_id=ID)
