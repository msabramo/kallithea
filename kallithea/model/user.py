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
kallithea.model.user
~~~~~~~~~~~~~~~~~~~~

users model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 9, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import traceback
from pylons.i18n.translation import _

from sqlalchemy.exc import DatabaseError

from kallithea import EXTERN_TYPE_INTERNAL
from kallithea.lib.utils2 import safe_unicode, generate_api_key, get_current_authuser
from kallithea.lib.caching_query import FromCache
from kallithea.model import BaseModel
from kallithea.model.db import User, UserToPerm, Notification, \
    UserEmailMap, UserIpMap
from kallithea.lib.exceptions import DefaultUserException, \
    UserOwnsReposException
from kallithea.model.meta import Session


log = logging.getLogger(__name__)


class UserModel(BaseModel):
    cls = User

    def get(self, user_id, cache=False):
        user = self.sa.query(User)
        if cache:
            user = user.options(FromCache("sql_cache_short",
                                          "get_user_%s" % user_id))
        return user.get(user_id)

    def get_user(self, user):
        return self._get_user(user)

    def get_by_username(self, username, cache=False, case_insensitive=False):

        if case_insensitive:
            user = self.sa.query(User).filter(User.username.ilike(username))
        else:
            user = self.sa.query(User)\
                .filter(User.username == username)
        if cache:
            user = user.options(FromCache("sql_cache_short",
                                          "get_user_%s" % username))
        return user.scalar()

    def get_by_email(self, email, cache=False, case_insensitive=False):
        return User.get_by_email(email, case_insensitive, cache)

    def get_by_api_key(self, api_key, cache=False):
        return User.get_by_api_key(api_key, cache)

    def create(self, form_data, cur_user=None):
        if not cur_user:
            cur_user = getattr(get_current_authuser(), 'username', None)

        from kallithea.lib.hooks import log_create_user, check_allowed_create_user
        _fd = form_data
        user_data = {
            'username': _fd['username'], 'password': _fd['password'],
            'email': _fd['email'], 'firstname': _fd['firstname'], 'lastname': _fd['lastname'],
            'active': _fd['active'], 'admin': False
        }
        # raises UserCreationError if it's not allowed
        check_allowed_create_user(user_data, cur_user)
        from kallithea.lib.auth import get_crypt_password
        try:
            new_user = User()
            for k, v in form_data.items():
                if k == 'password':
                    v = get_crypt_password(v)
                if k == 'firstname':
                    k = 'name'
                setattr(new_user, k, v)

            new_user.api_key = generate_api_key(form_data['username'])
            self.sa.add(new_user)

            log_create_user(new_user.get_dict(), cur_user)
            return new_user
        except Exception:
            log.error(traceback.format_exc())
            raise

    def create_or_update(self, username, password, email, firstname='',
                         lastname='', active=True, admin=False,
                         extern_type=None, extern_name=None, cur_user=None):
        """
        Creates a new instance if not found, or updates current one

        :param username:
        :param password:
        :param email:
        :param active:
        :param firstname:
        :param lastname:
        :param active:
        :param admin:
        :param extern_name:
        :param extern_type:
        :param cur_user:
        """
        if not cur_user:
            cur_user = getattr(get_current_authuser(), 'username', None)

        from kallithea.lib.auth import get_crypt_password, check_password
        from kallithea.lib.hooks import log_create_user, check_allowed_create_user
        user_data = {
            'username': username, 'password': password,
            'email': email, 'firstname': firstname, 'lastname': lastname,
            'active': active, 'admin': admin
        }
        # raises UserCreationError if it's not allowed
        check_allowed_create_user(user_data, cur_user)

        log.debug('Checking for %s account in Kallithea database' % username)
        user = User.get_by_username(username, case_insensitive=True)
        if user is None:
            log.debug('creating new user %s' % username)
            new_user = User()
            edit = False
        else:
            log.debug('updating user %s' % username)
            new_user = user
            edit = True

        try:
            new_user.username = username
            new_user.admin = admin
            new_user.email = email
            new_user.active = active
            new_user.extern_name = safe_unicode(extern_name) if extern_name else None
            new_user.extern_type = safe_unicode(extern_type) if extern_type else None
            new_user.name = firstname
            new_user.lastname = lastname

            if not edit:
                new_user.api_key = generate_api_key(username)

            # set password only if creating an user or password is changed
            password_change = new_user.password and not check_password(password,
                                                            new_user.password)
            if not edit or password_change:
                reason = 'new password' if edit else 'new user'
                log.debug('Updating password reason=>%s' % (reason,))
                new_user.password = get_crypt_password(password) if password else None

            self.sa.add(new_user)

            if not edit:
                log_create_user(new_user.get_dict(), cur_user)
            return new_user
        except (DatabaseError,):
            log.error(traceback.format_exc())
            raise

    def create_registration(self, form_data):
        from kallithea.model.notification import NotificationModel
        import kallithea.lib.helpers as h

        try:
            form_data['admin'] = False
            form_data['extern_name'] = EXTERN_TYPE_INTERNAL
            form_data['extern_type'] = EXTERN_TYPE_INTERNAL
            new_user = self.create(form_data)

            self.sa.add(new_user)
            self.sa.flush()

            # notification to admins
            subject = _('New user registration')
            body = ('New user registration\n'
                    '---------------------\n'
                    '- Username: %s\n'
                    '- Full Name: %s\n'
                    '- Email: %s\n')
            body = body % (new_user.username, new_user.full_name, new_user.email)
            edit_url = h.canonical_url('edit_user', id=new_user.user_id)
            email_kwargs = {'registered_user_url': edit_url, 'new_username': new_user.username}
            NotificationModel().create(created_by=new_user, subject=subject,
                                       body=body, recipients=None,
                                       type_=Notification.TYPE_REGISTRATION,
                                       email_kwargs=email_kwargs)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def update(self, user_id, form_data, skip_attrs=[]):
        from kallithea.lib.auth import get_crypt_password
        try:
            user = self.get(user_id, cache=False)
            if user.username == User.DEFAULT_USER:
                raise DefaultUserException(
                                _("You can't Edit this user since it's "
                                  "crucial for entire application"))

            for k, v in form_data.items():
                if k in skip_attrs:
                    continue
                if k == 'new_password' and v:
                    user.password = get_crypt_password(v)
                else:
                    # old legacy thing orm models store firstname as name,
                    # need proper refactor to username
                    if k == 'firstname':
                        k = 'name'
                    setattr(user, k, v)
            self.sa.add(user)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def update_user(self, user, **kwargs):
        from kallithea.lib.auth import get_crypt_password
        try:
            user = self._get_user(user)
            if user.username == User.DEFAULT_USER:
                raise DefaultUserException(
                    _("You can't Edit this user since it's"
                      " crucial for entire application")
                )

            for k, v in kwargs.items():
                if k == 'password' and v:
                    v = get_crypt_password(v)

                setattr(user, k, v)
            self.sa.add(user)
            return user
        except Exception:
            log.error(traceback.format_exc())
            raise

    def delete(self, user, cur_user=None):
        if not cur_user:
            cur_user = getattr(get_current_authuser(), 'username', None)
        user = self._get_user(user)

        try:
            if user.username == User.DEFAULT_USER:
                raise DefaultUserException(
                    _(u"You can't remove this user since it's"
                      " crucial for entire application")
                )
            if user.repositories:
                repos = [x.repo_name for x in user.repositories]
                raise UserOwnsReposException(
                    _(u'user "%s" still owns %s repositories and cannot be '
                      'removed. Switch owners or remove those repositories. %s')
                    % (user.username, len(repos), ', '.join(repos))
                )
            self.sa.delete(user)

            from kallithea.lib.hooks import log_delete_user
            log_delete_user(user.get_dict(), cur_user)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def reset_password_link(self, data):
        from kallithea.lib.celerylib import tasks, run_task
        from kallithea.model.notification import EmailNotificationModel
        import kallithea.lib.helpers as h

        user_email = data['email']
        try:
            user = User.get_by_email(user_email)
            if user:
                log.debug('password reset user found %s' % user)
                link = h.canonical_url('reset_password_confirmation', key=user.api_key)
                reg_type = EmailNotificationModel.TYPE_PASSWORD_RESET
                body = EmailNotificationModel().get_email_tmpl(reg_type,
                                                               user=user.short_contact,
                                                               reset_url=link)
                log.debug('sending email')
                run_task(tasks.send_email, [user_email],
                         _("Password reset link"), body, body)
                log.info('send new password mail to %s' % user_email)
            else:
                log.debug("password reset email %s not found" % user_email)
        except Exception:
            log.error(traceback.format_exc())
            return False

        return True

    def reset_password(self, data):
        from kallithea.lib.celerylib import tasks, run_task
        from kallithea.lib import auth
        user_email = data['email']
        pre_db = True
        try:
            user = User.get_by_email(user_email)
            new_passwd = auth.PasswordGenerator().gen_password(8,
                            auth.PasswordGenerator.ALPHABETS_BIG_SMALL)
            if user:
                user.password = auth.get_crypt_password(new_passwd)
                Session().add(user)
                Session().commit()
                log.info('change password for %s' % user_email)
            if new_passwd is None:
                raise Exception('unable to generate new password')

            pre_db = False
            run_task(tasks.send_email, [user_email],
                     _('Your new password'),
                     _('Your new Kallithea password:%s') % (new_passwd,))
            log.info('send new password mail to %s' % user_email)

        except Exception:
            log.error('Failed to update user password')
            log.error(traceback.format_exc())
            if pre_db:
                # we rollback only if local db stuff fails. If it goes into
                # run_task, we're pass rollback state this wouldn't work then
                Session().rollback()

        return True

    def fill_data(self, auth_user, user_id=None, api_key=None, username=None):
        """
        Fetches auth_user by user_id,or api_key if present.
        Fills auth_user attributes with those taken from database.
        Additionally set's is_authenitated if lookup fails
        present in database

        :param auth_user: instance of user to set attributes
        :param user_id: user id to fetch by
        :param api_key: api key to fetch by
        :param username: username to fetch by
        """
        if user_id is None and api_key is None and username is None:
            raise Exception('You need to pass user_id, api_key or username')

        try:
            dbuser = None
            if user_id:
                dbuser = self.get(user_id)
            elif api_key:
                dbuser = self.get_by_api_key(api_key)
            elif username:
                dbuser = self.get_by_username(username)

            if dbuser is not None and dbuser.active:
                log.debug('filling %s data' % dbuser)
                for k, v in dbuser.get_dict().iteritems():
                    if k not in ['api_keys', 'permissions']:
                        setattr(auth_user, k, v)
            else:
                return False

        except Exception:
            log.error(traceback.format_exc())
            auth_user.is_authenticated = False
            return False

        return True

    def has_perm(self, user, perm):
        perm = self._get_perm(perm)
        user = self._get_user(user)

        return UserToPerm.query().filter(UserToPerm.user == user)\
            .filter(UserToPerm.permission == perm).scalar() is not None

    def grant_perm(self, user, perm):
        """
        Grant user global permissions

        :param user:
        :param perm:
        """
        user = self._get_user(user)
        perm = self._get_perm(perm)
        # if this permission is already granted skip it
        _perm = UserToPerm.query()\
            .filter(UserToPerm.user == user)\
            .filter(UserToPerm.permission == perm)\
            .scalar()
        if _perm:
            return
        new = UserToPerm()
        new.user = user
        new.permission = perm
        self.sa.add(new)
        return new

    def revoke_perm(self, user, perm):
        """
        Revoke users global permissions

        :param user:
        :param perm:
        """
        user = self._get_user(user)
        perm = self._get_perm(perm)

        obj = UserToPerm.query()\
                .filter(UserToPerm.user == user)\
                .filter(UserToPerm.permission == perm)\
                .scalar()
        if obj:
            self.sa.delete(obj)

    def add_extra_email(self, user, email):
        """
        Adds email address to UserEmailMap

        :param user:
        :param email:
        """
        from kallithea.model import forms
        form = forms.UserExtraEmailForm()()
        data = form.to_python(dict(email=email))
        user = self._get_user(user)

        obj = UserEmailMap()
        obj.user = user
        obj.email = data['email']
        self.sa.add(obj)
        return obj

    def delete_extra_email(self, user, email_id):
        """
        Removes email address from UserEmailMap

        :param user:
        :param email_id:
        """
        user = self._get_user(user)
        obj = UserEmailMap.query().get(email_id)
        if obj:
            self.sa.delete(obj)

    def add_extra_ip(self, user, ip):
        """
        Adds ip address to UserIpMap

        :param user:
        :param ip:
        """
        from kallithea.model import forms
        form = forms.UserExtraIpForm()()
        data = form.to_python(dict(ip=ip))
        user = self._get_user(user)

        obj = UserIpMap()
        obj.user = user
        obj.ip_addr = data['ip']
        self.sa.add(obj)
        return obj

    def delete_extra_ip(self, user, ip_id):
        """
        Removes ip address from UserIpMap

        :param user:
        :param ip_id:
        """
        user = self._get_user(user)
        obj = UserIpMap.query().get(ip_id)
        if obj:
            self.sa.delete(obj)
