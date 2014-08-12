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
kallithea.controllers.admin.my_account
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

my account controller for Kallithea admin

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: August 20, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback
import formencode

from sqlalchemy import func
from formencode import htmlfill
from pylons import request, tmpl_context as c, url
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

from kallithea import EXTERN_TYPE_INTERNAL
from kallithea.lib import helpers as h
from kallithea.lib.auth import LoginRequired, NotAnonymous, AuthUser
from kallithea.lib.base import BaseController, render
from kallithea.lib.utils2 import generate_api_key, safe_int
from kallithea.lib.compat import json
from kallithea.model.db import Repository, \
    UserEmailMap, UserApiKeys, User, UserFollowing
from kallithea.model.forms import UserForm, PasswordChangeForm
from kallithea.model.user import UserModel
from kallithea.model.repo import RepoModel
from kallithea.model.api_key import ApiKeyModel
from kallithea.model.meta import Session

log = logging.getLogger(__name__)


class MyAccountController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""
    # To properly map this controller, ensure your config/routing.py
    # file has a resource setup:
    #     map.resource('setting', 'settings', controller='admin/settings',
    #         path_prefix='/admin', name_prefix='admin_')

    @LoginRequired()
    @NotAnonymous()
    def __before__(self):
        super(MyAccountController, self).__before__()

    def __load_data(self):
        c.user = User.get(self.authuser.user_id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user since it's"
                      " crucial for entire application"), category='warning')
            return redirect(url('users'))
        c.EXTERN_TYPE_INTERNAL = EXTERN_TYPE_INTERNAL

    def _load_my_repos_data(self, watched=False):
        if watched:
            admin = False
            repos_list = [x.follows_repository for x in
                          Session().query(UserFollowing).filter(
                              UserFollowing.user_id ==
                              self.authuser.user_id).all()]
        else:
            admin = True
            repos_list = Session().query(Repository)\
                         .filter(Repository.user_id ==
                                 self.authuser.user_id)\
                         .order_by(func.lower(Repository.repo_name)).all()

        repos_data = RepoModel().get_repos_as_dict(repos_list=repos_list,
                                                   admin=admin)
        #json used to render the grid
        return json.dumps(repos_data)

    def my_account(self):
        """
        GET /_admin/my_account Displays info about my account
        """
        # url('my_account')
        c.active = 'profile'
        self.__load_data()
        c.perm_user = AuthUser(user_id=self.authuser.user_id,
                               ip_addr=self.ip_addr)
        c.extern_type = c.user.extern_type
        c.extern_name = c.user.extern_name

        defaults = c.user.get_dict()
        update = False
        if request.POST:
            _form = UserForm(edit=True,
                             old_data={'user_id': self.authuser.user_id,
                                       'email': self.authuser.email})()
            form_result = {}
            try:
                post_data = dict(request.POST)
                post_data['new_password'] = ''
                post_data['password_confirmation'] = ''
                form_result = _form.to_python(post_data)
                # skip updating those attrs for my account
                skip_attrs = ['admin', 'active', 'extern_type', 'extern_name',
                              'new_password', 'password_confirmation']
                #TODO: plugin should define if username can be updated
                if c.extern_type != EXTERN_TYPE_INTERNAL:
                    # forbid updating username for external accounts
                    skip_attrs.append('username')

                UserModel().update(self.authuser.user_id, form_result,
                                   skip_attrs=skip_attrs)
                h.flash(_('Your account was updated successfully'),
                        category='success')
                Session().commit()
                update = True

            except formencode.Invalid, errors:
                return htmlfill.render(
                    render('admin/my_account/my_account.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8")
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during update of user %s') \
                        % form_result.get('username'), category='error')
        if update:
            return redirect('my_account')
        return htmlfill.render(
            render('admin/my_account/my_account.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    def my_account_password(self):
        c.active = 'password'
        self.__load_data()
        if request.POST:
            _form = PasswordChangeForm(self.authuser.username)()
            try:
                form_result = _form.to_python(request.POST)
                UserModel().update(self.authuser.user_id, form_result)
                Session().commit()
                h.flash(_("Successfully updated password"), category='success')
            except formencode.Invalid as errors:
                return htmlfill.render(
                    render('admin/my_account/my_account.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8")
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during update of user password'),
                        category='error')
        return render('admin/my_account/my_account.html')

    def my_account_repos(self):
        c.active = 'repos'
        self.__load_data()

        #json used to render the grid
        c.data = self._load_my_repos_data()
        return render('admin/my_account/my_account.html')

    def my_account_watched(self):
        c.active = 'watched'
        self.__load_data()

        #json used to render the grid
        c.data = self._load_my_repos_data(watched=True)
        return render('admin/my_account/my_account.html')

    def my_account_perms(self):
        c.active = 'perms'
        self.__load_data()
        c.perm_user = AuthUser(user_id=self.authuser.user_id,
                               ip_addr=self.ip_addr)

        return render('admin/my_account/my_account.html')

    def my_account_emails(self):
        c.active = 'emails'
        self.__load_data()

        c.user_email_map = UserEmailMap.query()\
            .filter(UserEmailMap.user == c.user).all()
        return render('admin/my_account/my_account.html')

    def my_account_emails_add(self):
        email = request.POST.get('new_email')

        try:
            UserModel().add_extra_email(self.authuser.user_id, email)
            Session().commit()
            h.flash(_("Added email %s to user") % email, category='success')
        except formencode.Invalid, error:
            msg = error.error_dict['email']
            h.flash(msg, category='error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during email saving'),
                    category='error')
        return redirect(url('my_account_emails'))

    def my_account_emails_delete(self):
        email_id = request.POST.get('del_email_id')
        user_model = UserModel()
        user_model.delete_extra_email(self.authuser.user_id, email_id)
        Session().commit()
        h.flash(_("Removed email from user"), category='success')
        return redirect(url('my_account_emails'))

    def my_account_api_keys(self):
        c.active = 'api_keys'
        self.__load_data()
        show_expired = True
        c.lifetime_values = [
            (str(-1), _('forever')),
            (str(5), _('5 minutes')),
            (str(60), _('1 hour')),
            (str(60 * 24), _('1 day')),
            (str(60 * 24 * 30), _('1 month')),
        ]
        c.lifetime_options = [(c.lifetime_values, _("Lifetime"))]
        c.user_api_keys = ApiKeyModel().get_api_keys(self.authuser.user_id,
                                                     show_expired=show_expired)
        return render('admin/my_account/my_account.html')

    def my_account_api_keys_add(self):
        lifetime = safe_int(request.POST.get('lifetime'), -1)
        description = request.POST.get('description')
        ApiKeyModel().create(self.authuser.user_id, description, lifetime)
        Session().commit()
        h.flash(_("Api key successfully created"), category='success')
        return redirect(url('my_account_api_keys'))

    def my_account_api_keys_delete(self):
        api_key = request.POST.get('del_api_key')
        user_id = self.authuser.user_id
        if request.POST.get('del_api_key_builtin'):
            user = User.get(user_id)
            if user:
                user.api_key = generate_api_key(user.username)
                Session().add(user)
                Session().commit()
                h.flash(_("Api key successfully reset"), category='success')
        elif api_key:
            ApiKeyModel().delete(api_key, self.authuser.user_id)
            Session().commit()
            h.flash(_("Api key successfully deleted"), category='success')

        return redirect(url('my_account_api_keys'))
