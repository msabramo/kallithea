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
kallithea.controllers.admin.permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

permissions controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 27, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import traceback
import formencode
from formencode import htmlfill

from pylons import request, tmpl_context as c, url
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

from kallithea.lib import helpers as h
from kallithea.lib.auth import LoginRequired, HasPermissionAllDecorator,\
    AuthUser
from kallithea.lib.base import BaseController, render
from kallithea.model.forms import DefaultPermissionsForm
from kallithea.model.permission import PermissionModel
from kallithea.model.db import User, UserIpMap
from kallithea.model.meta import Session

log = logging.getLogger(__name__)


class PermissionsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""
    # To properly map this controller, ensure your config/routing.py
    # file has a resource setup:
    #     map.resource('permission', 'permissions')

    @LoginRequired()
    @HasPermissionAllDecorator('hg.admin')
    def __before__(self):
        super(PermissionsController, self).__before__()

    def __load_data(self):
        c.repo_perms_choices = [('repository.none', _('None'),),
                                   ('repository.read', _('Read'),),
                                   ('repository.write', _('Write'),),
                                   ('repository.admin', _('Admin'),)]
        c.group_perms_choices = [('group.none', _('None'),),
                                 ('group.read', _('Read'),),
                                 ('group.write', _('Write'),),
                                 ('group.admin', _('Admin'),)]
        c.user_group_perms_choices = [('usergroup.none', _('None'),),
                                      ('usergroup.read', _('Read'),),
                                      ('usergroup.write', _('Write'),),
                                      ('usergroup.admin', _('Admin'),)]
        c.register_choices = [
            ('hg.register.none',
                _('Disabled')),
            ('hg.register.manual_activate',
                _('Allowed with manual account activation')),
            ('hg.register.auto_activate',
                _('Allowed with automatic account activation')), ]

        c.extern_activate_choices = [
            ('hg.extern_activate.manual', _('Manual activation of external account')),
            ('hg.extern_activate.auto', _('Automatic activation of external account')),
        ]

        c.repo_create_choices = [('hg.create.none', _('Disabled')),
                                 ('hg.create.repository', _('Enabled'))]

        c.repo_create_on_write_choices = [
            ('hg.create.write_on_repogroup.true', _('Enabled')),
            ('hg.create.write_on_repogroup.false', _('Disabled')),
        ]

        c.user_group_create_choices = [('hg.usergroup.create.false', _('Disabled')),
                                       ('hg.usergroup.create.true', _('Enabled'))]

        c.repo_group_create_choices = [('hg.repogroup.create.false', _('Disabled')),
                                       ('hg.repogroup.create.true', _('Enabled'))]

        c.fork_choices = [('hg.fork.none', _('Disabled')),
                          ('hg.fork.repository', _('Enabled'))]

    def permission_globals(self):
        c.active = 'globals'
        self.__load_data()
        if request.POST:
            _form = DefaultPermissionsForm(
                [x[0] for x in c.repo_perms_choices],
                [x[0] for x in c.group_perms_choices],
                [x[0] for x in c.user_group_perms_choices],
                [x[0] for x in c.repo_create_choices],
                [x[0] for x in c.repo_create_on_write_choices],
                [x[0] for x in c.repo_group_create_choices],
                [x[0] for x in c.user_group_create_choices],
                [x[0] for x in c.fork_choices],
                [x[0] for x in c.register_choices],
                [x[0] for x in c.extern_activate_choices])()

            try:
                form_result = _form.to_python(dict(request.POST))
                form_result.update({'perm_user_name': 'default'})
                PermissionModel().update(form_result)
                Session().commit()
                h.flash(_('Global permissions updated successfully'),
                        category='success')

            except formencode.Invalid, errors:
                defaults = errors.value

                return htmlfill.render(
                    render('admin/permissions/permissions.html'),
                    defaults=defaults,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8")
            except Exception:
                log.error(traceback.format_exc())
                h.flash(_('Error occurred during update of permissions'),
                        category='error')

            return redirect(url('admin_permissions'))

        c.user = User.get_default_user()
        defaults = {'anonymous': c.user.active}

        for p in c.user.user_perms:
            if p.permission.permission_name.startswith('repository.'):
                defaults['default_repo_perm'] = p.permission.permission_name

            if p.permission.permission_name.startswith('group.'):
                defaults['default_group_perm'] = p.permission.permission_name

            if p.permission.permission_name.startswith('usergroup.'):
                defaults['default_user_group_perm'] = p.permission.permission_name

            if p.permission.permission_name.startswith('hg.create.write_on_repogroup'):
                defaults['create_on_write'] = p.permission.permission_name

            elif p.permission.permission_name.startswith('hg.create.'):
                defaults['default_repo_create'] = p.permission.permission_name

            if p.permission.permission_name.startswith('hg.repogroup.'):
                defaults['default_repo_group_create'] = p.permission.permission_name

            if p.permission.permission_name.startswith('hg.usergroup.'):
                defaults['default_user_group_create'] = p.permission.permission_name

            if p.permission.permission_name.startswith('hg.register.'):
                defaults['default_register'] = p.permission.permission_name

            if p.permission.permission_name.startswith('hg.extern_activate.'):
                defaults['default_extern_activate'] = p.permission.permission_name

            if p.permission.permission_name.startswith('hg.fork.'):
                defaults['default_fork'] = p.permission.permission_name

        return htmlfill.render(
            render('admin/permissions/permissions.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False)

    def permission_ips(self):
        c.active = 'ips'
        c.user = User.get_default_user()
        c.user_ip_map = UserIpMap.query()\
                        .filter(UserIpMap.user == c.user).all()

        return render('admin/permissions/permissions.html')

    def permission_perms(self):
        c.active = 'perms'
        c.user = User.get_default_user()
        c.perm_user = c.user.AuthUser
        return render('admin/permissions/permissions.html')
