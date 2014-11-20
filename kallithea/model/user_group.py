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
kallithea.model.users_group
~~~~~~~~~~~~~~~~~~~~~~~~~~~

user group model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Oct 1, 2011
:author: nvinot, marcink
"""


import logging
import traceback

from kallithea.model import BaseModel
from kallithea.model.db import UserGroupMember, UserGroup,\
    UserGroupRepoToPerm, Permission, UserGroupToPerm, User, UserUserGroupToPerm,\
    UserGroupUserGroupToPerm
from kallithea.lib.exceptions import UserGroupsAssignedException,\
    RepoGroupAssignmentError

log = logging.getLogger(__name__)


class UserGroupModel(BaseModel):

    cls = UserGroup

    def _get_user_group(self, user_group):
        return self._get_instance(UserGroup, user_group,
                                  callback=UserGroup.get_by_group_name)

    def _create_default_perms(self, user_group):
        # create default permission
        default_perm = 'usergroup.read'
        def_user = User.get_default_user()
        for p in def_user.user_perms:
            if p.permission.permission_name.startswith('usergroup.'):
                default_perm = p.permission.permission_name
                break

        user_group_to_perm = UserUserGroupToPerm()
        user_group_to_perm.permission = Permission.get_by_key(default_perm)

        user_group_to_perm.user_group = user_group
        user_group_to_perm.user_id = def_user.user_id
        return user_group_to_perm

    def _update_permissions(self, user_group, perms_new=None,
                            perms_updates=None):
        from kallithea.lib.auth import HasUserGroupPermissionAny
        if not perms_new:
            perms_new = []
        if not perms_updates:
            perms_updates = []

        # update permissions
        for member, perm, member_type in perms_updates:
            if member_type == 'user':
                # this updates existing one
                self.grant_user_permission(
                    user_group=user_group, user=member, perm=perm
                )
            else:
                #check if we have permissions to alter this usergroup
                if HasUserGroupPermissionAny('usergroup.read', 'usergroup.write',
                                             'usergroup.admin')(member):
                    self.grant_user_group_permission(
                        target_user_group=user_group, user_group=member, perm=perm
                    )
        # set new permissions
        for member, perm, member_type in perms_new:
            if member_type == 'user':
                self.grant_user_permission(
                    user_group=user_group, user=member, perm=perm
                )
            else:
                #check if we have permissions to alter this usergroup
                if HasUserGroupPermissionAny('usergroup.read', 'usergroup.write',
                                             'usergroup.admin')(member):
                    self.grant_user_group_permission(
                        target_user_group=user_group, user_group=member, perm=perm
                    )

    def get(self, user_group_id, cache=False):
        return UserGroup.get(user_group_id)

    def get_group(self, user_group):
        return self._get_user_group(user_group)

    def get_by_name(self, name, cache=False, case_insensitive=False):
        return UserGroup.get_by_group_name(name, cache, case_insensitive)

    def create(self, name, description, owner, active=True, group_data=None):
        try:
            new_user_group = UserGroup()
            new_user_group.user = self._get_user(owner)
            new_user_group.users_group_name = name
            new_user_group.user_group_description = description
            new_user_group.users_group_active = active
            if group_data:
                new_user_group.group_data = group_data
            self.sa.add(new_user_group)
            perm_obj = self._create_default_perms(new_user_group)
            self.sa.add(perm_obj)

            self.grant_user_permission(user_group=new_user_group,
                                       user=owner, perm='usergroup.admin')

            return new_user_group
        except Exception:
            log.error(traceback.format_exc())
            raise

    def update(self, user_group, form_data):

        try:
            user_group = self._get_user_group(user_group)

            for k, v in form_data.items():
                if k == 'users_group_members':
                    user_group.members = []
                    self.sa.flush()
                    members_list = []
                    if v:
                        v = [v] if isinstance(v, basestring) else v
                        for u_id in set(v):
                            member = UserGroupMember(user_group.users_group_id, u_id)
                            members_list.append(member)
                    setattr(user_group, 'members', members_list)
                setattr(user_group, k, v)

            self.sa.add(user_group)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def delete(self, user_group, force=False):
        """
        Deletes repository group, unless force flag is used
        raises exception if there are members in that group, else deletes
        group and users

        :param user_group:
        :param force:
        """
        user_group = self._get_user_group(user_group)
        try:
            # check if this group is not assigned to repo
            assigned_groups = UserGroupRepoToPerm.query()\
                .filter(UserGroupRepoToPerm.users_group == user_group).all()

            if assigned_groups and not force:
                raise UserGroupsAssignedException(
                    'RepoGroup assigned to %s' % assigned_groups)
            self.sa.delete(user_group)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def add_user_to_group(self, user_group, user):
        user_group = self._get_user_group(user_group)
        user = self._get_user(user)

        for m in user_group.members:
            u = m.user
            if u.user_id == user.user_id:
                # user already in the group, skip
                return True

        try:
            user_group_member = UserGroupMember()
            user_group_member.user = user
            user_group_member.users_group = user_group

            user_group.members.append(user_group_member)
            user.group_member.append(user_group_member)

            self.sa.add(user_group_member)
            return user_group_member
        except Exception:
            log.error(traceback.format_exc())
            raise

    def remove_user_from_group(self, user_group, user):
        user_group = self._get_user_group(user_group)
        user = self._get_user(user)

        user_group_member = None
        for m in user_group.members:
            if m.user.user_id == user.user_id:
                # Found this user's membership row
                user_group_member = m
                break

        if user_group_member:
            try:
                self.sa.delete(user_group_member)
                return True
            except Exception:
                log.error(traceback.format_exc())
                raise
        else:
            # User isn't in that group
            return False

    def has_perm(self, user_group, perm):
        user_group = self._get_user_group(user_group)
        perm = self._get_perm(perm)

        return UserGroupToPerm.query()\
            .filter(UserGroupToPerm.users_group == user_group)\
            .filter(UserGroupToPerm.permission == perm).scalar() is not None

    def grant_perm(self, user_group, perm):
        user_group = self._get_user_group(user_group)
        perm = self._get_perm(perm)

        # if this permission is already granted skip it
        _perm = UserGroupToPerm.query()\
            .filter(UserGroupToPerm.users_group == user_group)\
            .filter(UserGroupToPerm.permission == perm)\
            .scalar()
        if _perm:
            return

        new = UserGroupToPerm()
        new.users_group = user_group
        new.permission = perm
        self.sa.add(new)
        return new

    def revokehas_permrevoke_permgrant_perm_perm(self, user_group, perm):
        user_group = self._get_user_group(user_group)
        perm = self._get_perm(perm)

        obj = UserGroupToPerm.query()\
            .filter(UserGroupToPerm.users_group == user_group)\
            .filter(UserGroupToPerm.permission == perm).scalar()
        if obj:
            self.sa.delete(obj)

    def grant_user_permission(self, user_group, user, perm):
        """
        Grant permission for user on given user group, or update
        existing one if found

        :param user_group: Instance of UserGroup, users_group_id,
            or users_group_name
        :param user: Instance of User, user_id or username
        :param perm: Instance of Permission, or permission_name
        """

        user_group = self._get_user_group(user_group)
        user = self._get_user(user)
        permission = self._get_perm(perm)

        # check if we have that permission already
        obj = self.sa.query(UserUserGroupToPerm)\
            .filter(UserUserGroupToPerm.user == user)\
            .filter(UserUserGroupToPerm.user_group == user_group)\
            .scalar()
        if obj is None:
            # create new !
            obj = UserUserGroupToPerm()
        obj.user_group = user_group
        obj.user = user
        obj.permission = permission
        self.sa.add(obj)
        log.debug('Granted perm %s to %s on %s' % (perm, user, user_group))
        return obj

    def revoke_user_permission(self, user_group, user):
        """
        Revoke permission for user on given repository group

        :param user_group: Instance of RepoGroup, repositories_group_id,
            or repositories_group name
        :param user: Instance of User, user_id or username
        """

        user_group = self._get_user_group(user_group)
        user = self._get_user(user)

        obj = self.sa.query(UserUserGroupToPerm)\
            .filter(UserUserGroupToPerm.user == user)\
            .filter(UserUserGroupToPerm.user_group == user_group)\
            .scalar()
        if obj:
            self.sa.delete(obj)
            log.debug('Revoked perm on %s on %s' % (user_group, user))

    def grant_user_group_permission(self, target_user_group, user_group, perm):
        """
        Grant user group permission for given target_user_group

        :param target_user_group:
        :param user_group:
        :param perm:
        """
        target_user_group = self._get_user_group(target_user_group)
        user_group = self._get_user_group(user_group)
        permission = self._get_perm(perm)
        # forbid assigning same user group to itself
        if target_user_group == user_group:
            raise RepoGroupAssignmentError('target repo:%s cannot be '
                                           'assigned to itself' % target_user_group)

        # check if we have that permission already
        obj = self.sa.query(UserGroupUserGroupToPerm)\
            .filter(UserGroupUserGroupToPerm.target_user_group == target_user_group)\
            .filter(UserGroupUserGroupToPerm.user_group == user_group)\
            .scalar()
        if obj is None:
            # create new !
            obj = UserGroupUserGroupToPerm()
        obj.user_group = user_group
        obj.target_user_group = target_user_group
        obj.permission = permission
        self.sa.add(obj)
        log.debug('Granted perm %s to %s on %s' % (perm, target_user_group, user_group))
        return obj

    def revoke_user_group_permission(self, target_user_group, user_group):
        """
        Revoke user group permission for given target_user_group

        :param target_user_group:
        :param user_group:
        """
        target_user_group = self._get_user_group(target_user_group)
        user_group = self._get_user_group(user_group)

        obj = self.sa.query(UserGroupUserGroupToPerm)\
            .filter(UserGroupUserGroupToPerm.target_user_group == target_user_group)\
            .filter(UserGroupUserGroupToPerm.user_group == user_group)\
            .scalar()
        if obj:
            self.sa.delete(obj)
            log.debug('Revoked perm on %s on %s' % (target_user_group, user_group))

    def enforce_groups(self, user, groups, extern_type=None):
        user = self._get_user(user)
        log.debug('Enforcing groups %s on user %s' % (user, groups))
        current_groups = user.group_member
        # find the external created groups
        externals = [x.users_group for x in current_groups
                     if 'extern_type' in x.users_group.group_data]

        # calculate from what groups user should be removed
        # externals that are not in groups
        for gr in externals:
            if gr.users_group_name not in groups:
                log.debug('Removing user %s from user group %s' % (user, gr))
                self.remove_user_from_group(gr, user)

        # now we calculate in which groups user should be == groups params
        owner = User.get_first_admin().username
        for gr in set(groups):
            existing_group = UserGroup.get_by_group_name(gr)
            if not existing_group:
                desc = 'Automatically created from plugin:%s' % extern_type
                # we use first admin account to set the owner of the group
                existing_group = UserGroupModel().create(gr, desc, owner,
                                        group_data={'extern_type': extern_type})

            # we can only add users to special groups created via plugins
            managed = 'extern_type' in existing_group.group_data
            if managed:
                log.debug('Adding user %s to user group %s' % (user, gr))
                UserGroupModel().add_user_to_group(existing_group, user)
            else:
                log.debug('Skipping addition to group %s since it is '
                          'not managed by auth plugins' % gr)
