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
kallithea.controllers.admin.users
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users crud controller for pylons

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 4, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback
import formencode

from formencode import htmlfill
from pylons import request, tmpl_context as c, url, config
from pylons.controllers.util import redirect
from pylons.i18n.translation import _
from sqlalchemy.sql.expression import func

import kallithea
from kallithea.lib.exceptions import DefaultUserException, \
    UserOwnsReposException, UserCreationError
from kallithea.lib import helpers as h
from kallithea.lib.auth import LoginRequired, HasPermissionAllDecorator, \
    AuthUser, generate_api_key
import kallithea.lib.auth_modules.auth_internal
from kallithea.lib import auth_modules
from kallithea.lib.base import BaseController, render
from kallithea.model.api_key import ApiKeyModel

from kallithea.model.db import User, UserEmailMap, UserIpMap, UserToPerm
from kallithea.model.forms import UserForm, CustomDefaultPermissionsForm
from kallithea.model.user import UserModel
from kallithea.model.meta import Session
from kallithea.lib.utils import action_logger
from kallithea.lib.compat import json
from kallithea.lib.utils2 import datetime_to_time, safe_int

log = logging.getLogger(__name__)


class UsersController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""

    @LoginRequired()
    @HasPermissionAllDecorator('hg.admin')
    def __before__(self):
        super(UsersController, self).__before__()
        c.available_permissions = config['available_permissions']
        c.EXTERN_TYPE_INTERNAL = kallithea.EXTERN_TYPE_INTERNAL

    def index(self, format='html'):
        """GET /users: All items in the collection"""
        # url('users')

        c.users_list = User.query().order_by(User.username)\
                        .filter(User.username != User.DEFAULT_USER)\
                        .order_by(func.lower(User.username))\
                        .all()

        users_data = []
        total_records = len(c.users_list)
        _tmpl_lookup = kallithea.CONFIG['pylons.app_globals'].mako_lookup
        template = _tmpl_lookup.get_template('data_table/_dt_elements.html')

        grav_tmpl = lambda user_email, size: (
                template.get_def("user_gravatar")
                .render(user_email, size, _=_, h=h, c=c))

        username = lambda user_id, username: (
                template.get_def("user_name")
                .render(user_id, username, _=_, h=h, c=c))

        user_actions = lambda user_id, username: (
                template.get_def("user_actions")
                .render(user_id, username, _=_, h=h, c=c))

        for user in c.users_list:

            users_data.append({
                "gravatar": grav_tmpl(user. email, 20),
                "raw_name": user.username,
                "username": username(user.user_id, user.username),
                "firstname": user.name,
                "lastname": user.lastname,
                "last_login": h.fmt_date(user.last_login),
                "last_login_raw": datetime_to_time(user.last_login),
                "active": h.boolicon(user.active),
                "admin": h.boolicon(user.admin),
                "extern_type": user.extern_type,
                "extern_name": user.extern_name,
                "action": user_actions(user.user_id, user.username),
            })

        c.data = json.dumps({
            "totalRecords": total_records,
            "startIndex": 0,
            "sort": None,
            "dir": "asc",
            "records": users_data
        })

        return render('admin/users/users.html')

    def create(self):
        """POST /users: Create a new item"""
        # url('users')
        c.default_extern_type = auth_modules.auth_internal.KallitheaAuthPlugin.name
        user_model = UserModel()
        user_form = UserForm()()
        try:
            form_result = user_form.to_python(dict(request.POST))
            user_model.create(form_result)
            usr = form_result['username']
            action_logger(self.authuser, 'admin_created_user:%s' % usr,
                          None, self.ip_addr, self.sa)
            h.flash(_('Created user %s') % usr,
                    category='success')
            Session().commit()
        except formencode.Invalid, errors:
            return htmlfill.render(
                render('admin/users/user_add.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8")
        except UserCreationError, e:
            h.flash(e, 'error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during creation of user %s') \
                    % request.POST.get('username'), category='error')
        return redirect(url('users'))

    def new(self, format='html'):
        """GET /users/new: Form to create a new item"""
        # url('new_user')
        c.default_extern_type = auth_modules.auth_internal.KallitheaAuthPlugin.name
        return render('admin/users/user_add.html')

    def update(self, id):
        """PUT /users/id: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('update_user', id=ID),
        #           method='put')
        # url('user', id=ID)
        c.active = 'profile'
        user_model = UserModel()
        c.user = user_model.get(id)
        c.extern_type = c.user.extern_type
        c.extern_name = c.user.extern_name
        c.perm_user = AuthUser(user_id=id, ip_addr=self.ip_addr)
        _form = UserForm(edit=True, old_data={'user_id': id,
                                              'email': c.user.email})()
        form_result = {}
        try:
            form_result = _form.to_python(dict(request.POST))
            skip_attrs = ['extern_type', 'extern_name']
            #TODO: plugin should define if username can be updated
            if c.extern_type != kallithea.EXTERN_TYPE_INTERNAL:
                # forbid updating username for external accounts
                skip_attrs.append('username')

            user_model.update(id, form_result, skip_attrs=skip_attrs)
            usr = form_result['username']
            action_logger(self.authuser, 'admin_updated_user:%s' % usr,
                          None, self.ip_addr, self.sa)
            h.flash(_('User updated successfully'), category='success')
            Session().commit()
        except formencode.Invalid, errors:
            defaults = errors.value
            e = errors.error_dict or {}
            defaults.update({
                'create_repo_perm': user_model.has_perm(id,
                                                        'hg.create.repository'),
                'fork_repo_perm': user_model.has_perm(id, 'hg.fork.repository'),
                '_method': 'put'
            })
            return htmlfill.render(
                render('admin/users/user_edit.html'),
                defaults=defaults,
                errors=e,
                prefix_error=False,
                encoding="UTF-8")
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during update of user %s') \
                    % form_result.get('username'), category='error')
        return redirect(url('edit_user', id=id))

    def delete(self, id):
        """DELETE /users/id: Delete an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="DELETE" />
        # Or using helpers:
        #    h.form(url('delete_user', id=ID),
        #           method='delete')
        # url('user', id=ID)
        usr = User.get_or_404(id)
        try:
            UserModel().delete(usr)
            Session().commit()
            h.flash(_('Successfully deleted user'), category='success')
        except (UserOwnsReposException, DefaultUserException), e:
            h.flash(e, category='warning')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during deletion of user'),
                    category='error')
        return redirect(url('users'))

    def show(self, id, format='html'):
        """GET /users/id: Show a specific item"""
        # url('user', id=ID)
        User.get_or_404(-1)

    def edit(self, id, format='html'):
        """GET /users/id/edit: Form to edit an existing item"""
        # url('edit_user', id=ID)
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        c.active = 'profile'
        c.extern_type = c.user.extern_type
        c.extern_name = c.user.extern_name
        c.perm_user = AuthUser(user_id=id, ip_addr=self.ip_addr)

        defaults = c.user.get_dict()
        return htmlfill.render(
            render('admin/users/user_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    def edit_advanced(self, id):
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        c.active = 'advanced'
        c.perm_user = AuthUser(user_id=id, ip_addr=self.ip_addr)

        umodel = UserModel()
        defaults = c.user.get_dict()
        defaults.update({
            'create_repo_perm': umodel.has_perm(c.user, 'hg.create.repository'),
            'create_user_group_perm': umodel.has_perm(c.user,
                                                      'hg.usergroup.create.true'),
            'fork_repo_perm': umodel.has_perm(c.user, 'hg.fork.repository'),
        })
        return htmlfill.render(
            render('admin/users/user_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    def edit_api_keys(self, id):
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        c.active = 'api_keys'
        show_expired = True
        c.lifetime_values = [
            (str(-1), _('forever')),
            (str(5), _('5 minutes')),
            (str(60), _('1 hour')),
            (str(60 * 24), _('1 day')),
            (str(60 * 24 * 30), _('1 month')),
        ]
        c.lifetime_options = [(c.lifetime_values, _("Lifetime"))]
        c.user_api_keys = ApiKeyModel().get_api_keys(c.user.user_id,
                                                     show_expired=show_expired)
        defaults = c.user.get_dict()
        return htmlfill.render(
            render('admin/users/user_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    def add_api_key(self, id):
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        lifetime = safe_int(request.POST.get('lifetime'), -1)
        description = request.POST.get('description')
        ApiKeyModel().create(c.user.user_id, description, lifetime)
        Session().commit()
        h.flash(_("Api key successfully created"), category='success')
        return redirect(url('edit_user_api_keys', id=c.user.user_id))

    def delete_api_key(self, id):
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        api_key = request.POST.get('del_api_key')
        if request.POST.get('del_api_key_builtin'):
            user = User.get(c.user.user_id)
            if user:
                user.api_key = generate_api_key(user.username)
                Session().add(user)
                Session().commit()
                h.flash(_("Api key successfully reset"), category='success')
        elif api_key:
            ApiKeyModel().delete(api_key, c.user.user_id)
            Session().commit()
            h.flash(_("Api key successfully deleted"), category='success')

        return redirect(url('edit_user_api_keys', id=c.user.user_id))

    def update_account(self, id):
        pass

    def edit_perms(self, id):
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        c.active = 'perms'
        c.perm_user = AuthUser(user_id=id, ip_addr=self.ip_addr)

        umodel = UserModel()
        defaults = c.user.get_dict()
        defaults.update({
            'create_repo_perm': umodel.has_perm(c.user, 'hg.create.repository'),
            'create_user_group_perm': umodel.has_perm(c.user,
                                                      'hg.usergroup.create.true'),
            'fork_repo_perm': umodel.has_perm(c.user, 'hg.fork.repository'),
        })
        return htmlfill.render(
            render('admin/users/user_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    def update_perms(self, id):
        """PUT /users_perm/id: Update an existing item"""
        # url('user_perm', id=ID, method='put')
        user = User.get_or_404(id)

        try:
            form = CustomDefaultPermissionsForm()()
            form_result = form.to_python(request.POST)

            inherit_perms = form_result['inherit_default_permissions']
            user.inherit_default_permissions = inherit_perms
            Session().add(user)
            user_model = UserModel()

            defs = UserToPerm.query()\
                .filter(UserToPerm.user == user)\
                .all()
            for ug in defs:
                Session().delete(ug)

            if form_result['create_repo_perm']:
                user_model.grant_perm(id, 'hg.create.repository')
            else:
                user_model.grant_perm(id, 'hg.create.none')
            if form_result['create_user_group_perm']:
                user_model.grant_perm(id, 'hg.usergroup.create.true')
            else:
                user_model.grant_perm(id, 'hg.usergroup.create.false')
            if form_result['fork_repo_perm']:
                user_model.grant_perm(id, 'hg.fork.repository')
            else:
                user_model.grant_perm(id, 'hg.fork.none')
            h.flash(_("Updated permissions"), category='success')
            Session().commit()
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during permissions saving'),
                    category='error')
        return redirect(url('edit_user_perms', id=id))

    def edit_emails(self, id):
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        c.active = 'emails'
        c.user_email_map = UserEmailMap.query()\
            .filter(UserEmailMap.user == c.user).all()

        defaults = c.user.get_dict()
        return htmlfill.render(
            render('admin/users/user_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    def add_email(self, id):
        """POST /user_emails:Add an existing item"""
        # url('user_emails', id=ID, method='put')

        email = request.POST.get('new_email')
        user_model = UserModel()

        try:
            user_model.add_extra_email(id, email)
            Session().commit()
            h.flash(_("Added email %s to user") % email, category='success')
        except formencode.Invalid, error:
            msg = error.error_dict['email']
            h.flash(msg, category='error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during email saving'),
                    category='error')
        return redirect(url('edit_user_emails', id=id))

    def delete_email(self, id):
        """DELETE /user_emails_delete/id: Delete an existing item"""
        # url('user_emails_delete', id=ID, method='delete')
        email_id = request.POST.get('del_email_id')
        user_model = UserModel()
        user_model.delete_extra_email(id, email_id)
        Session().commit()
        h.flash(_("Removed email from user"), category='success')
        return redirect(url('edit_user_emails', id=id))

    def edit_ips(self, id):
        c.user = User.get_or_404(id)
        if c.user.username == User.DEFAULT_USER:
            h.flash(_("You can't edit this user"), category='warning')
            return redirect(url('users'))

        c.active = 'ips'
        c.user_ip_map = UserIpMap.query()\
            .filter(UserIpMap.user == c.user).all()

        c.inherit_default_ips = c.user.inherit_default_permissions
        c.default_user_ip_map = UserIpMap.query()\
            .filter(UserIpMap.user == User.get_default_user()).all()

        defaults = c.user.get_dict()
        return htmlfill.render(
            render('admin/users/user_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    def add_ip(self, id):
        """POST /user_ips:Add an existing item"""
        # url('user_ips', id=ID, method='put')

        ip = request.POST.get('new_ip')
        user_model = UserModel()

        try:
            user_model.add_extra_ip(id, ip)
            Session().commit()
            h.flash(_("Added ip %s to user whitelist") % ip, category='success')
        except formencode.Invalid, error:
            msg = error.error_dict['ip']
            h.flash(msg, category='error')
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during ip saving'),
                    category='error')

        if 'default_user' in request.POST:
            return redirect(url('admin_permissions_ips'))
        return redirect(url('edit_user_ips', id=id))

    def delete_ip(self, id):
        """DELETE /user_ips_delete/id: Delete an existing item"""
        # url('user_ips_delete', id=ID, method='delete')
        ip_id = request.POST.get('del_ip_id')
        user_model = UserModel()
        user_model.delete_extra_ip(id, ip_id)
        Session().commit()
        h.flash(_("Removed ip address from user whitelist"), category='success')

        if 'default_user' in request.POST:
            return redirect(url('admin_permissions_ips'))
        return redirect(url('edit_user_ips', id=id))
