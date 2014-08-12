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
kallithea.controllers.admin.repo_groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Repository groups controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Mar 23, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
import traceback
import formencode
import itertools

from formencode import htmlfill

from pylons import request, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.i18n.translation import _, ungettext

import kallithea
from kallithea.lib import helpers as h
from kallithea.lib.compat import json
from kallithea.lib.auth import LoginRequired, HasPermissionAnyDecorator,\
    HasRepoGroupPermissionAnyDecorator, HasRepoGroupPermissionAll,\
    HasPermissionAll
from kallithea.lib.base import BaseController, render
from kallithea.model.db import RepoGroup, Repository
from kallithea.model.scm import RepoGroupList
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.forms import RepoGroupForm, RepoGroupPermsForm
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from webob.exc import HTTPInternalServerError, HTTPNotFound
from kallithea.lib.utils2 import safe_int
from sqlalchemy.sql.expression import func


log = logging.getLogger(__name__)


class RepoGroupsController(BaseController):
    """REST Controller styled on the Atom Publishing Protocol"""

    @LoginRequired()
    def __before__(self):
        super(RepoGroupsController, self).__before__()

    def __load_defaults(self, allow_empty_group=False, exclude_group_ids=[]):
        if HasPermissionAll('hg.admin')('group edit'):
            #we're global admin, we're ok and we can create TOP level groups
            allow_empty_group = True

        #override the choices for this form, we need to filter choices
        #and display only those we have ADMIN right
        groups_with_admin_rights = RepoGroupList(RepoGroup.query().all(),
                                                 perm_set=['group.admin'])
        c.repo_groups = RepoGroup.groups_choices(groups=groups_with_admin_rights,
                                                 show_empty_group=allow_empty_group)
        # exclude filtered ids
        c.repo_groups = filter(lambda x: x[0] not in exclude_group_ids,
                               c.repo_groups)
        c.repo_groups_choices = map(lambda k: unicode(k[0]), c.repo_groups)
        repo_model = RepoModel()
        c.users_array = repo_model.get_users_js()
        c.user_groups_array = repo_model.get_user_groups_js()

    def __load_data(self, group_id):
        """
        Load defaults settings for edit, and update

        :param group_id:
        """
        repo_group = RepoGroup.get_or_404(group_id)
        data = repo_group.get_dict()
        data['group_name'] = repo_group.name

        # fill repository group users
        for p in repo_group.repo_group_to_perm:
            data.update({'u_perm_%s' % p.user.username:
                             p.permission.permission_name})

        # fill repository group groups
        for p in repo_group.users_group_to_perm:
            data.update({'g_perm_%s' % p.users_group.users_group_name:
                             p.permission.permission_name})

        return data

    def _revoke_perms_on_yourself(self, form_result):
        _up = filter(lambda u: c.authuser.username == u[0],
                     form_result['perms_updates'])
        _new = filter(lambda u: c.authuser.username == u[0],
                      form_result['perms_new'])
        if _new and _new[0][1] != 'group.admin' or _up and _up[0][1] != 'group.admin':
            return True
        return False

    def index(self, format='html'):
        """GET /repo_groups: All items in the collection"""
        # url('repos_groups')
        _list = RepoGroup.query()\
                    .order_by(func.lower(RepoGroup.group_name))\
                    .all()
        group_iter = RepoGroupList(_list, perm_set=['group.admin'])
        repo_groups_data = []
        total_records = len(group_iter)
        _tmpl_lookup = kallithea.CONFIG['pylons.app_globals'].mako_lookup
        template = _tmpl_lookup.get_template('data_table/_dt_elements.html')

        repo_group_name = lambda repo_group_name, children_groups: (
            template.get_def("repo_group_name")
            .render(repo_group_name, children_groups, _=_, h=h, c=c)
        )
        repo_group_actions = lambda repo_group_id, repo_group_name, gr_count: (
            template.get_def("repo_group_actions")
            .render(repo_group_id, repo_group_name, gr_count, _=_, h=h, c=c,
                    ungettext=ungettext)
        )

        for repo_gr in group_iter:
            children_groups = map(h.safe_unicode,
                itertools.chain((g.name for g in repo_gr.parents),
                                (x.name for x in [repo_gr])))
            repo_count = repo_gr.repositories.count()
            repo_groups_data.append({
                "raw_name": repo_gr.group_name,
                "group_name": repo_group_name(repo_gr.group_name, children_groups),
                "desc": repo_gr.group_description,
                "repos": repo_count,
                "owner": h.person(repo_gr.user.username),
                "action": repo_group_actions(repo_gr.group_id, repo_gr.group_name,
                                             repo_count)
            })

        c.data = json.dumps({
            "totalRecords": total_records,
            "startIndex": 0,
            "sort": None,
            "dir": "asc",
            "records": repo_groups_data
        })

        return render('admin/repo_groups/repo_groups.html')

    def create(self):
        """POST /repo_groups: Create a new item"""
        # url('repos_groups')

        self.__load_defaults()

        # permissions for can create group based on parent_id are checked
        # here in the Form
        repo_group_form = RepoGroupForm(available_groups=
                                map(lambda k: unicode(k[0]), c.repo_groups))()
        try:
            form_result = repo_group_form.to_python(dict(request.POST))
            RepoGroupModel().create(
                group_name=form_result['group_name'],
                group_description=form_result['group_description'],
                parent=form_result['group_parent_id'],
                owner=self.authuser.user_id,
                copy_permissions=form_result['group_copy_permissions']
            )
            Session().commit()
            h.flash(_('Created repository group %s') \
                    % form_result['group_name'], category='success')
            #TODO: in futureaction_logger(, '', '', '', self.sa)
        except formencode.Invalid, errors:
            return htmlfill.render(
                render('admin/repo_groups/repo_group_add.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8")
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during creation of repository group %s') \
                    % request.POST.get('group_name'), category='error')
        parent_group_id = form_result['group_parent_id']
        #TODO: maybe we should get back to the main view, not the admin one
        return redirect(url('repos_groups', parent_group=parent_group_id))

    def new(self):
        """GET /repo_groups/new: Form to create a new item"""
        # url('new_repos_group')
        if HasPermissionAll('hg.admin')('group create'):
            #we're global admin, we're ok and we can create TOP level groups
            pass
        else:
            # we pass in parent group into creation form, thus we know
            # what would be the group, we can check perms here !
            group_id = safe_int(request.GET.get('parent_group'))
            group = RepoGroup.get(group_id) if group_id else None
            group_name = group.group_name if group else None
            if HasRepoGroupPermissionAll('group.admin')(group_name, 'group create'):
                pass
            else:
                return abort(403)

        self.__load_defaults()
        return render('admin/repo_groups/repo_group_add.html')

    @HasRepoGroupPermissionAnyDecorator('group.admin')
    def update(self, group_name):
        """PUT /repo_groups/group_name: Update an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="PUT" />
        # Or using helpers:
        #    h.form(url('repos_group', group_name=GROUP_NAME),
        #           method='put')
        # url('repos_group', group_name=GROUP_NAME)

        c.repo_group = RepoGroupModel()._get_repo_group(group_name)
        if HasPermissionAll('hg.admin')('group edit'):
            #we're global admin, we're ok and we can create TOP level groups
            allow_empty_group = True
        elif not c.repo_group.parent_group:
            allow_empty_group = True
        else:
            allow_empty_group = False
        self.__load_defaults(allow_empty_group=allow_empty_group,
                             exclude_group_ids=[c.repo_group.group_id])

        repo_group_form = RepoGroupForm(
            edit=True,
            old_data=c.repo_group.get_dict(),
            available_groups=c.repo_groups_choices,
            can_create_in_root=allow_empty_group,
        )()
        try:
            form_result = repo_group_form.to_python(dict(request.POST))

            new_gr = RepoGroupModel().update(group_name, form_result)
            Session().commit()
            h.flash(_('Updated repository group %s') \
                    % form_result['group_name'], category='success')
            # we now have new name !
            group_name = new_gr.group_name
            #TODO: in future action_logger(, '', '', '', self.sa)
        except formencode.Invalid, errors:

            return htmlfill.render(
                render('admin/repo_groups/repo_group_edit.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8")
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during update of repository group %s') \
                    % request.POST.get('group_name'), category='error')

        return redirect(url('edit_repo_group', group_name=group_name))

    @HasRepoGroupPermissionAnyDecorator('group.admin')
    def delete(self, group_name):
        """DELETE /repo_groups/group_name: Delete an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="DELETE" />
        # Or using helpers:
        #    h.form(url('repos_group', group_name=GROUP_NAME),
        #           method='delete')
        # url('repos_group', group_name=GROUP_NAME)

        gr = c.repo_group = RepoGroupModel()._get_repo_group(group_name)
        repos = gr.repositories.all()
        if repos:
            h.flash(_('This group contains %s repositores and cannot be '
                      'deleted') % len(repos), category='warning')
            return redirect(url('repos_groups'))

        children = gr.children.all()
        if children:
            h.flash(_('This group contains %s subgroups and cannot be deleted'
                      % (len(children))), category='warning')
            return redirect(url('repos_groups'))

        try:
            RepoGroupModel().delete(group_name)
            Session().commit()
            h.flash(_('Removed repository group %s') % group_name,
                    category='success')
            #TODO: in future action_logger(, '', '', '', self.sa)
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('Error occurred during deletion of repository group %s')
                    % group_name, category='error')

        if gr.parent_group:
            return redirect(url('repos_group_home', group_name=gr.parent_group.group_name))
        return redirect(url('repos_groups'))

    def show_by_name(self, group_name):
        """
        This is a proxy that does a lookup group_name -> id, and shows
        the group by id view instead
        """
        group_name = group_name.rstrip('/')
        id_ = RepoGroup.get_by_group_name(group_name)
        if id_:
            return self.show(group_name)
        raise HTTPNotFound

    @HasRepoGroupPermissionAnyDecorator('group.read', 'group.write',
                                         'group.admin')
    def show(self, group_name):
        """GET /repo_groups/group_name: Show a specific item"""
        # url('repos_group', group_name=GROUP_NAME)
        c.active = 'settings'

        c.group = c.repo_group = RepoGroupModel()._get_repo_group(group_name)
        c.group_repos = c.group.repositories.all()

        #overwrite our cached list with current filter
        c.repo_cnt = 0

        groups = RepoGroup.query().order_by(RepoGroup.group_name)\
            .filter(RepoGroup.group_parent_id == c.group.group_id).all()
        c.groups = self.scm_model.get_repo_groups(groups)

        c.repos_list = Repository.query()\
                        .filter(Repository.group_id == c.group.group_id)\
                        .order_by(func.lower(Repository.repo_name))\
                        .all()

        repos_data = RepoModel().get_repos_as_dict(repos_list=c.repos_list,
                                                   admin=False)
        #json used to render the grid
        c.data = json.dumps(repos_data)

        return render('admin/repo_groups/repo_group_show.html')

    @HasRepoGroupPermissionAnyDecorator('group.admin')
    def edit(self, group_name):
        """GET /repo_groups/group_name/edit: Form to edit an existing item"""
        # url('edit_repo_group', group_name=GROUP_NAME)
        c.active = 'settings'

        c.repo_group = RepoGroupModel()._get_repo_group(group_name)
        #we can only allow moving empty group if it's already a top-level
        #group, ie has no parents, or we're admin
        if HasPermissionAll('hg.admin')('group edit'):
            #we're global admin, we're ok and we can create TOP level groups
            allow_empty_group = True
        elif not c.repo_group.parent_group:
            allow_empty_group = True
        else:
            allow_empty_group = False

        self.__load_defaults(allow_empty_group=allow_empty_group,
                             exclude_group_ids=[c.repo_group.group_id])
        defaults = self.__load_data(c.repo_group.group_id)

        return htmlfill.render(
            render('admin/repo_groups/repo_group_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasRepoGroupPermissionAnyDecorator('group.admin')
    def edit_repo_group_advanced(self, group_name):
        """GET /repo_groups/group_name/edit: Form to edit an existing item"""
        # url('edit_repo_group', group_name=GROUP_NAME)
        c.active = 'advanced'
        c.repo_group = RepoGroupModel()._get_repo_group(group_name)

        return render('admin/repo_groups/repo_group_edit.html')

    @HasRepoGroupPermissionAnyDecorator('group.admin')
    def edit_repo_group_perms(self, group_name):
        """GET /repo_groups/group_name/edit: Form to edit an existing item"""
        # url('edit_repo_group', group_name=GROUP_NAME)
        c.active = 'perms'
        c.repo_group = RepoGroupModel()._get_repo_group(group_name)
        self.__load_defaults()
        defaults = self.__load_data(c.repo_group.group_id)

        return htmlfill.render(
            render('admin/repo_groups/repo_group_edit.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasRepoGroupPermissionAnyDecorator('group.admin')
    def update_perms(self, group_name):
        """
        Update permissions for given repository group

        :param group_name:
        """

        c.repo_group = RepoGroupModel()._get_repo_group(group_name)
        valid_recursive_choices = ['none', 'repos', 'groups', 'all']
        form_result = RepoGroupPermsForm(valid_recursive_choices)().to_python(request.POST)
        if not c.authuser.is_admin:
            if self._revoke_perms_on_yourself(form_result):
                msg = _('Cannot revoke permission for yourself as admin')
                h.flash(msg, category='warning')
                return redirect(url('edit_repo_group_perms', group_name=group_name))
        recursive = form_result['recursive']
        # iterate over all members(if in recursive mode) of this groups and
        # set the permissions !
        # this can be potentially heavy operation
        RepoGroupModel()._update_permissions(c.repo_group,
                                             form_result['perms_new'],
                                             form_result['perms_updates'],
                                             recursive)
        #TODO: implement this
        #action_logger(self.authuser, 'admin_changed_repo_permissions',
        #              repo_name, self.ip_addr, self.sa)
        Session().commit()
        h.flash(_('Repository Group permissions updated'), category='success')
        return redirect(url('edit_repo_group_perms', group_name=group_name))

    @HasRepoGroupPermissionAnyDecorator('group.admin')
    def delete_perms(self, group_name):
        """
        DELETE an existing repository group permission user

        :param group_name:
        """
        try:
            obj_type = request.POST.get('obj_type')
            obj_id = None
            if obj_type == 'user':
                obj_id = safe_int(request.POST.get('user_id'))
            elif obj_type == 'user_group':
                obj_id = safe_int(request.POST.get('user_group_id'))

            if not c.authuser.is_admin:
                if obj_type == 'user' and c.authuser.user_id == obj_id:
                    msg = _('Cannot revoke permission for yourself as admin')
                    h.flash(msg, category='warning')
                    raise Exception('revoke admin permission on self')
            recursive = request.POST.get('recursive', 'none')
            if obj_type == 'user':
                RepoGroupModel().delete_permission(repo_group=group_name,
                                                   obj=obj_id, obj_type='user',
                                                   recursive=recursive)
            elif obj_type == 'user_group':
                RepoGroupModel().delete_permission(repo_group=group_name,
                                                   obj=obj_id,
                                                   obj_type='user_group',
                                                   recursive=recursive)

            Session().commit()
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during revoking of permission'),
                    category='error')
            raise HTTPInternalServerError()
