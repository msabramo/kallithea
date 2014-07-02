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
kallithea.controllers.api
~~~~~~~~~~~~~~~~~~~~~~~~~

API controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Aug 20, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import time
import traceback
import logging
from sqlalchemy import or_

from kallithea import EXTERN_TYPE_INTERNAL
from kallithea.controllers.api import JSONRPCController, JSONRPCError
from kallithea.lib.auth import (
    PasswordGenerator, AuthUser, HasPermissionAllDecorator,
    HasPermissionAnyDecorator, HasPermissionAnyApi, HasRepoPermissionAnyApi,
    HasRepoGroupPermissionAnyApi, HasUserGroupPermissionAny)
from kallithea.lib.utils import map_groups, repo2db_mapper
from kallithea.lib.utils2 import (
    str2bool, time_to_datetime, safe_int, Optional, OAttr)
from kallithea.model.meta import Session
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.scm import ScmModel, UserGroupList
from kallithea.model.repo import RepoModel
from kallithea.model.user import UserModel
from kallithea.model.user_group import UserGroupModel
from kallithea.model.gist import GistModel
from kallithea.model.db import (
    Repository, Setting, UserIpMap, Permission, User, Gist,
    RepoGroup)
from kallithea.lib.compat import json
from kallithea.lib.exceptions import (
    DefaultUserException, UserGroupsAssignedException)

log = logging.getLogger(__name__)


def store_update(updates, attr, name):
    """
    Stores param in updates dict if it's not instance of Optional
    allows easy updates of passed in params
    """
    if not isinstance(attr, Optional):
        updates[name] = attr


def get_user_or_error(userid):
    """
    Get user by id or name or return JsonRPCError if not found

    :param userid:
    """
    user = UserModel().get_user(userid)
    if user is None:
        raise JSONRPCError("user `%s` does not exist" % (userid,))
    return user


def get_repo_or_error(repoid):
    """
    Get repo by id or name or return JsonRPCError if not found

    :param repoid:
    """
    repo = RepoModel().get_repo(repoid)
    if repo is None:
        raise JSONRPCError('repository `%s` does not exist' % (repoid,))
    return repo


def get_repo_group_or_error(repogroupid):
    """
    Get repo group by id or name or return JsonRPCError if not found

    :param repogroupid:
    """
    repo_group = RepoGroupModel()._get_repo_group(repogroupid)
    if repo_group is None:
        raise JSONRPCError(
            'repository group `%s` does not exist' % (repogroupid,))
    return repo_group


def get_user_group_or_error(usergroupid):
    """
    Get user group by id or name or return JsonRPCError if not found

    :param usergroupid:
    """
    user_group = UserGroupModel().get_group(usergroupid)
    if user_group is None:
        raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))
    return user_group


def get_perm_or_error(permid, prefix=None):
    """
    Get permission by id or name or return JsonRPCError if not found

    :param permid:
    """
    perm = Permission.get_by_key(permid)
    if perm is None:
        raise JSONRPCError('permission `%s` does not exist' % (permid,))
    if prefix:
        if not perm.permission_name.startswith(prefix):
            raise JSONRPCError('permission `%s` is invalid, '
                               'should start with %s' % (permid, prefix))
    return perm


def get_gist_or_error(gistid):
    """
    Get gist by id or gist_access_id or return JsonRPCError if not found

    :param gistid:
    """
    gist = GistModel().get_gist(gistid)
    if gist is None:
        raise JSONRPCError('gist `%s` does not exist' % (gistid,))
    return gist


class ApiController(JSONRPCController):
    """
    API Controller

    Each method takes USER as first argument. This is then, based on given
    API_KEY propagated as instance of user object who's making the call.

    example function::

        def func(apiuser,arg1, arg2,...):
            pass

    Each function should also **raise** JSONRPCError for any
    errors that happens.

    """

    @HasPermissionAllDecorator('hg.admin')
    def test(self, apiuser, args):
        return args

    @HasPermissionAllDecorator('hg.admin')
    def pull(self, apiuser, repoid):
        """
        Triggers a pull from remote location on given repo. Can be used to
        automatically keep remote repos up to date. This command can be executed
        only using api_key belonging to user with admin rights

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int

        OUTPUT::

          id : <id_given_in_input>
          result : {
            "msg": "Pulled from `<repository name>`"
            "repository": "<repository name>"
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "Unable to pull changes from `<reponame>`"
          }

        """

        repo = get_repo_or_error(repoid)

        try:
            ScmModel().pull_changes(repo.repo_name,
                                    self.authuser.username)
            return dict(
                msg='Pulled from `%s`' % repo.repo_name,
                repository=repo.repo_name
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'Unable to pull changes from `%s`' % repo.repo_name
            )

    @HasPermissionAllDecorator('hg.admin')
    def rescan_repos(self, apiuser, remove_obsolete=Optional(False)):
        """
        Triggers rescan repositories action. If remove_obsolete is set
        than also delete repos that are in database but not in the filesystem.
        aka "clean zombies". This command can be executed only using api_key
        belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param remove_obsolete: deletes repositories from
            database that are not found on the filesystem
        :type remove_obsolete: Optional(bool)

        OUTPUT::

          id : <id_given_in_input>
          result : {
            'added': [<added repository name>,...]
            'removed': [<removed repository name>,...]
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            'Error occurred during rescan repositories action'
          }

        """

        try:
            rm_obsolete = Optional.extract(remove_obsolete)
            added, removed = repo2db_mapper(ScmModel().repo_scan(),
                                            remove_obsolete=rm_obsolete)
            return {'added': added, 'removed': removed}
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'Error occurred during rescan repositories action'
            )

    def invalidate_cache(self, apiuser, repoid):
        """
        Invalidate cache for repository.
        This command can be executed only using api_key belonging to user with admin
        rights or regular user that have write or admin or write access to repository.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int

        OUTPUT::

          id : <id_given_in_input>
          result : {
            'msg': Cache for repository `<repository name>` was invalidated,
            'repository': <repository name>
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            'Error occurred during cache invalidation action'
          }

        """
        repo = get_repo_or_error(repoid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo !
            if not HasRepoPermissionAnyApi('repository.admin',
                                           'repository.write')(
                    user=apiuser, repo_name=repo.repo_name):
                raise JSONRPCError('repository `%s` does not exist' % (repoid,))

        try:
            ScmModel().mark_for_invalidation(repo.repo_name)
            return dict(
                msg='Cache for repository `%s` was invalidated' % (repoid,),
                repository=repo.repo_name
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'Error occurred during cache invalidation action'
            )

    # permission check inside
    def lock(self, apiuser, repoid, locked=Optional(None),
             userid=Optional(OAttr('apiuser'))):
        """
        Set locking state on given repository by given user. If userid param
        is skipped, then it is set to id of user whos calling this method.
        If locked param is skipped then function shows current lock state of
        given repo. This command can be executed only using api_key belonging
        to user with admin rights or regular user that have admin or write
        access to repository.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param locked: lock state to be set
        :type locked: Optional(bool)
        :param userid: set lock as user
        :type userid: Optional(str or int)

        OUTPUT::

          id : <id_given_in_input>
          result : {
            'repo': '<reponame>',
            'locked': <bool: lock state>,
            'locked_since': <int: lock timestamp>,
            'locked_by': <username of person who made the lock>,
            'lock_state_changed': <bool: True if lock state has been changed in this request>,
            'msg': 'Repo `<reponame>` locked by `<username>` on <timestamp>.'
            or
            'msg': 'Repo `<repository name>` not locked.'
            or
            'msg': 'User `<user name>` set lock state for repo `<repository name>` to `<new lock state>`'
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            'Error occurred locking repository `<reponame>`
          }

        """
        repo = get_repo_or_error(repoid)
        if HasPermissionAnyApi('hg.admin')(user=apiuser):
            pass
        elif HasRepoPermissionAnyApi('repository.admin',
                                     'repository.write')(user=apiuser,
                                                         repo_name=repo.repo_name):
            # make sure normal user does not pass someone else userid,
            # he is not allowed to do that
            if not isinstance(userid, Optional) and userid != apiuser.user_id:
                raise JSONRPCError(
                    'userid is not the same as your user'
                )
        else:
            raise JSONRPCError('repository `%s` does not exist' % (repoid,))

        if isinstance(userid, Optional):
            userid = apiuser.user_id

        user = get_user_or_error(userid)

        if isinstance(locked, Optional):
            lockobj = Repository.getlock(repo)

            if lockobj[0] is None:
                _d = {
                    'repo': repo.repo_name,
                    'locked': False,
                    'locked_since': None,
                    'locked_by': None,
                    'lock_state_changed': False,
                    'msg': 'Repo `%s` not locked.' % repo.repo_name
                }
                return _d
            else:
                userid, time_ = lockobj
                lock_user = get_user_or_error(userid)
                _d = {
                    'repo': repo.repo_name,
                    'locked': True,
                    'locked_since': time_,
                    'locked_by': lock_user.username,
                    'lock_state_changed': False,
                    'msg': ('Repo `%s` locked by `%s` on `%s`.'
                            % (repo.repo_name, lock_user.username,
                               json.dumps(time_to_datetime(time_))))
                }
                return _d

        # force locked state through a flag
        else:
            locked = str2bool(locked)
            try:
                if locked:
                    lock_time = time.time()
                    Repository.lock(repo, user.user_id, lock_time)
                else:
                    lock_time = None
                    Repository.unlock(repo)
                _d = {
                    'repo': repo.repo_name,
                    'locked': locked,
                    'locked_since': lock_time,
                    'locked_by': user.username,
                    'lock_state_changed': True,
                    'msg': ('User `%s` set lock state for repo `%s` to `%s`'
                            % (user.username, repo.repo_name, locked))
                }
                return _d
            except Exception:
                log.error(traceback.format_exc())
                raise JSONRPCError(
                    'Error occurred locking repository `%s`' % repo.repo_name
                )

    def get_locks(self, apiuser, userid=Optional(OAttr('apiuser'))):
        """
        Get all repositories with locks for given userid, if
        this command is runned by non-admin account userid is set to user
        who is calling this method, thus returning locks for himself.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param userid: User to get locks for
        :type userid: Optional(str or int)

        OUTPUT::

          id : <id_given_in_input>
          result : {
            [repo_object, repo_object,...]
          }
          error :  null
        """

        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # make sure normal user does not pass someone else userid,
            # he is not allowed to do that
            if not isinstance(userid, Optional) and userid != apiuser.user_id:
                raise JSONRPCError(
                    'userid is not the same as your user'
                )

        ret = []
        if isinstance(userid, Optional):
            user = None
        else:
            user = get_user_or_error(userid)

        # show all locks
        for r in Repository.getAll():
            userid, time_ = r.locked
            if time_:
                _api_data = r.get_api_data()
                # if we use userfilter just show the locks for this user
                if user:
                    if safe_int(userid) == user.user_id:
                        ret.append(_api_data)
                else:
                    ret.append(_api_data)

        return ret

    @HasPermissionAllDecorator('hg.admin')
    def get_ip(self, apiuser, userid=Optional(OAttr('apiuser'))):
        """
        Shows IP address as seen from Kallithea server, together with all
        defined IP addresses for given user. If userid is not passed data is
        returned for user who's calling this function.
        This command can be executed only using api_key belonging to user with
        admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param userid: username to show ips for
        :type userid: Optional(str or int)

        OUTPUT::

            id : <id_given_in_input>
            result : {
                         "server_ip_addr": "<ip_from_clien>",
                         "user_ips": [
                                        {
                                           "ip_addr": "<ip_with_mask>",
                                           "ip_range": ["<start_ip>", "<end_ip>"],
                                        },
                                        ...
                                     ]
            }

        """
        if isinstance(userid, Optional):
            userid = apiuser.user_id
        user = get_user_or_error(userid)
        ips = UserIpMap.query().filter(UserIpMap.user == user).all()
        return dict(
            server_ip_addr=self.ip_addr,
            user_ips=ips
        )

    # alias for old
    show_ip = get_ip

    @HasPermissionAllDecorator('hg.admin')
    def get_server_info(self, apiuser):
        """
        return server info, including Kallithea version and installed packages

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser

        OUTPUT::

          id : <id_given_in_input>
          result : {
            'modules': [<module name>,...]
            'py_version': <python version>,
            'platform': <platform type>,
            'kallithea_version': <kallithea version>
          }
          error :  null
        """
        return Setting.get_server_info()

    def get_user(self, apiuser, userid=Optional(OAttr('apiuser'))):
        """
        Get's an user by username or user_id, Returns empty result if user is
        not found. If userid param is skipped it is set to id of user who is
        calling this method. This command can be executed only using api_key
        belonging to user with admin rights, or regular users that cannot
        specify different userid than theirs

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param userid: user to get data for
        :type userid: Optional(str or int)

        OUTPUT::

            id : <id_given_in_input>
            result: None if user does not exist or
                    {
                        "user_id" :     "<user_id>",
                        "api_key" :     "<api_key>",
                        "api_keys":     "[<list of all api keys including additional ones>]"
                        "username" :    "<username>",
                        "firstname":    "<firstname>",
                        "lastname" :    "<lastname>",
                        "email" :       "<email>",
                        "emails":       "[<list of all emails including additional ones>]",
                        "ip_addresses": "[<ip_addresse_for_user>,...]",
                        "active" :      "<bool: user active>",
                        "admin" :       "<bool: user is admin>",
                        "extern_name" : "<extern_name>",
                        "extern_type" : "<extern type>
                        "last_login":   "<last_login>",
                        "permissions": {
                            "global": ["hg.create.repository",
                                       "repository.read",
                                       "hg.register.manual_activate"],
                            "repositories": {"repo1": "repository.none"},
                            "repositories_groups": {"Group1": "group.read"}
                         },
                    }

            error:  null

        """
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # make sure normal user does not pass someone else userid,
            # he is not allowed to do that
            if not isinstance(userid, Optional) and userid != apiuser.user_id:
                raise JSONRPCError(
                    'userid is not the same as your user'
                )

        if isinstance(userid, Optional):
            userid = apiuser.user_id

        user = get_user_or_error(userid)
        data = user.get_api_data()
        data['permissions'] = AuthUser(user_id=user.user_id).permissions
        return data

    @HasPermissionAllDecorator('hg.admin')
    def get_users(self, apiuser):
        """
        Lists all existing users. This command can be executed only using api_key
        belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser

        OUTPUT::

            id : <id_given_in_input>
            result: [<user_object>, ...]
            error:  null
        """

        result = []
        users_list = User.query().order_by(User.username) \
            .filter(User.username != User.DEFAULT_USER) \
            .all()
        for user in users_list:
            result.append(user.get_api_data())
        return result

    @HasPermissionAllDecorator('hg.admin')
    def create_user(self, apiuser, username, email, password=Optional(''),
                    firstname=Optional(''), lastname=Optional(''),
                    active=Optional(True), admin=Optional(False),
                    extern_name=Optional(EXTERN_TYPE_INTERNAL),
                    extern_type=Optional(EXTERN_TYPE_INTERNAL)):
        """
        Creates new user. Returns new user object. This command can
        be executed only using api_key belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param username: new username
        :type username: str or int
        :param email: email
        :type email: str
        :param password: password
        :type password: Optional(str)
        :param firstname: firstname
        :type firstname: Optional(str)
        :param lastname: lastname
        :type lastname: Optional(str)
        :param active: active
        :type active: Optional(bool)
        :param admin: admin
        :type admin: Optional(bool)
        :param extern_name: name of extern
        :type extern_name: Optional(str)
        :param extern_type: extern_type
        :type extern_type: Optional(str)


        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "created new user `<username>`",
                      "user": <user_obj>
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "user `<username>` already exist"
            or
            "email `<email>` already exist"
            or
            "failed to create user `<username>`"
          }

        """

        if UserModel().get_by_username(username):
            raise JSONRPCError("user `%s` already exist" % (username,))

        if UserModel().get_by_email(email, case_insensitive=True):
            raise JSONRPCError("email `%s` already exist" % (email,))

        if Optional.extract(extern_name):
            # generate temporary password if user is external
            password = PasswordGenerator().gen_password(length=8)

        try:
            user = UserModel().create_or_update(
                username=Optional.extract(username),
                password=Optional.extract(password),
                email=Optional.extract(email),
                firstname=Optional.extract(firstname),
                lastname=Optional.extract(lastname),
                active=Optional.extract(active),
                admin=Optional.extract(admin),
                extern_type=Optional.extract(extern_type),
                extern_name=Optional.extract(extern_name)
            )
            Session().commit()
            return dict(
                msg='created new user `%s`' % username,
                user=user.get_api_data()
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to create user `%s`' % (username,))

    @HasPermissionAllDecorator('hg.admin')
    def update_user(self, apiuser, userid, username=Optional(None),
                    email=Optional(None),password=Optional(None),
                    firstname=Optional(None), lastname=Optional(None),
                    active=Optional(None), admin=Optional(None),
                    extern_type=Optional(None), extern_name=Optional(None),):
        """
        updates given user if such user exists. This command can
        be executed only using api_key belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param userid: userid to update
        :type userid: str or int
        :param username: new username
        :type username: str or int
        :param email: email
        :type email: str
        :param password: password
        :type password: Optional(str)
        :param firstname: firstname
        :type firstname: Optional(str)
        :param lastname: lastname
        :type lastname: Optional(str)
        :param active: active
        :type active: Optional(bool)
        :param admin: admin
        :type admin: Optional(bool)
        :param extern_name:
        :type extern_name: Optional(str)
        :param extern_type:
        :type extern_type: Optional(str)


        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "updated user ID:<userid> <username>",
                      "user": <user_object>,
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to update user `<username>`"
          }

        """

        user = get_user_or_error(userid)

        # only non optional arguments will be stored in updates
        updates = {}

        try:

            store_update(updates, username, 'username')
            store_update(updates, password, 'password')
            store_update(updates, email, 'email')
            store_update(updates, firstname, 'name')
            store_update(updates, lastname, 'lastname')
            store_update(updates, active, 'active')
            store_update(updates, admin, 'admin')
            store_update(updates, extern_name, 'extern_name')
            store_update(updates, extern_type, 'extern_type')

            user = UserModel().update_user(user, **updates)
            Session().commit()
            return dict(
                msg='updated user ID:%s %s' % (user.user_id, user.username),
                user=user.get_api_data()
            )
        except DefaultUserException:
            log.error(traceback.format_exc())
            raise JSONRPCError('editing default user is forbidden')
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to update user `%s`' % (userid,))

    @HasPermissionAllDecorator('hg.admin')
    def delete_user(self, apiuser, userid):
        """
        deletes givenuser if such user exists. This command can
        be executed only using api_key belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param userid: user to delete
        :type userid: str or int

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "deleted user ID:<userid> <username>",
                      "user": null
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to delete user ID:<userid> <username>"
          }

        """
        user = get_user_or_error(userid)

        try:
            UserModel().delete(userid)
            Session().commit()
            return dict(
                msg='deleted user ID:%s %s' % (user.user_id, user.username),
                user=None
            )
        except Exception:

            log.error(traceback.format_exc())
            raise JSONRPCError('failed to delete user ID:%s %s'
                               % (user.user_id, user.username))

    # permission check inside
    def get_user_group(self, apiuser, usergroupid):
        """
        Gets an existing user group. This command can be executed only using api_key
        belonging to user with admin rights or user who has at least
        read access to user group.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param usergroupid: id of user_group to edit
        :type usergroupid: str or int

        OUTPUT::

            id : <id_given_in_input>
            result : None if group not exist
                     {
                       "users_group_id" : "<id>",
                       "group_name" :     "<groupname>",
                       "active":          "<bool>",
                       "members" :  [<user_obj>,...]
                     }
            error : null

        """
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have at least read permission for this user group !
            _perms = ('usergroup.read', 'usergroup.write', 'usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))

        data = user_group.get_api_data()
        return data

    # permission check inside
    def get_user_groups(self, apiuser):
        """
        Lists all existing user groups. This command can be executed only using
        api_key belonging to user with admin rights or user who has at least
        read access to user group.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser

        OUTPUT::

            id : <id_given_in_input>
            result : [<user_group_obj>,...]
            error : null
        """

        result = []
        _perms = ('usergroup.read', 'usergroup.write', 'usergroup.admin',)
        extras = {'user': apiuser}
        for user_group in UserGroupList(UserGroupModel().get_all(),
                                        perm_set=_perms, extra_kwargs=extras):
            result.append(user_group.get_api_data())
        return result

    @HasPermissionAnyDecorator('hg.admin', 'hg.usergroup.create.true')
    def create_user_group(self, apiuser, group_name, description=Optional(''),
                          owner=Optional(OAttr('apiuser')), active=Optional(True)):
        """
        Creates new user group. This command can be executed only using api_key
        belonging to user with admin rights or an user who has create user group
        permission

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param group_name: name of new user group
        :type group_name: str
        :param description: group description
        :type description: str
        :param owner: owner of group. If not passed apiuser is the owner
        :type owner: Optional(str or int)
        :param active: group is active
        :type active: Optional(bool)

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg": "created new user group `<groupname>`",
                      "user_group": <user_group_object>
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "user group `<group name>` already exist"
            or
            "failed to create group `<group name>`"
          }

        """

        if UserGroupModel().get_by_name(group_name):
            raise JSONRPCError("user group `%s` already exist" % (group_name,))

        try:
            if isinstance(owner, Optional):
                owner = apiuser.user_id

            owner = get_user_or_error(owner)
            active = Optional.extract(active)
            description = Optional.extract(description)
            ug = UserGroupModel().create(name=group_name, description=description,
                                         owner=owner, active=active)
            Session().commit()
            return dict(
                msg='created new user group `%s`' % group_name,
                user_group=ug.get_api_data()
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to create group `%s`' % (group_name,))

    # permission check inside
    def update_user_group(self, apiuser, usergroupid, group_name=Optional(''),
                          description=Optional(''), owner=Optional(None),
                          active=Optional(True)):
        """
        Updates given usergroup.  This command can be executed only using api_key
        belonging to user with admin rights or an admin of given user group

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param usergroupid: id of user group to update
        :type usergroupid: str or int
        :param group_name: name of new user group
        :type group_name: str
        :param description: group description
        :type description: str
        :param owner: owner of group.
        :type owner: Optional(str or int)
        :param active: group is active
        :type active: Optional(bool)

        OUTPUT::

          id : <id_given_in_input>
          result : {
            "msg": 'updated user group ID:<user group id> <user group name>',
            "user_group": <user_group_object>
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to update user group `<user group name>`"
          }

        """
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this user group !
            _perms = ('usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))

        if not isinstance(owner, Optional):
            owner = get_user_or_error(owner)

        updates = {}
        store_update(updates, group_name, 'users_group_name')
        store_update(updates, description, 'user_group_description')
        store_update(updates, owner, 'user')
        store_update(updates, active, 'users_group_active')
        try:
            UserGroupModel().update(user_group, updates)
            Session().commit()
            return dict(
                msg='updated user group ID:%s %s' % (user_group.users_group_id,
                                                     user_group.users_group_name),
                user_group=user_group.get_api_data()
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to update user group `%s`' % (usergroupid,))

    # permission check inside
    def delete_user_group(self, apiuser, usergroupid):
        """
        Delete given user group by user group id or name.
        This command can be executed only using api_key
        belonging to user with admin rights or an admin of given user group

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param usergroupid:
        :type usergroupid: int

        OUTPUT::

          id : <id_given_in_input>
          result : {
            "msg": "deleted user group ID:<user_group_id> <user_group_name>"
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to delete user group ID:<user_group_id> <user_group_name>"
            or
            "RepoGroup assigned to <repo_groups_list>"
          }

        """
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this user group !
            _perms = ('usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))

        try:
            UserGroupModel().delete(user_group)
            Session().commit()
            return dict(
                msg='deleted user group ID:%s %s' %
                    (user_group.users_group_id, user_group.users_group_name),
                user_group=None
            )
        except UserGroupsAssignedException, e:
            log.error(traceback.format_exc())
            raise JSONRPCError(str(e))
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to delete user group ID:%s %s' %
                               (user_group.users_group_id,
                                user_group.users_group_name)
            )

    # permission check inside
    def add_user_to_user_group(self, apiuser, usergroupid, userid):
        """
        Adds a user to a user group. If user exists in that group success will be
        `false`. This command can be executed only using api_key
        belonging to user with admin rights  or an admin of given user group

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param usergroupid:
        :type usergroupid: int
        :param userid:
        :type userid: int

        OUTPUT::

          id : <id_given_in_input>
          result : {
              "success": True|False # depends on if member is in group
              "msg": "added member `<username>` to user group `<groupname>` |
                      User is already in that group"

          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to add member to user group `<user_group_name>`"
          }

        """
        user = get_user_or_error(userid)
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this user group !
            _perms = ('usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))

        try:
            ugm = UserGroupModel().add_user_to_group(user_group, user)
            success = True if ugm != True else False
            msg = 'added member `%s` to user group `%s`' % (
                user.username, user_group.users_group_name
            )
            msg = msg if success else 'User is already in that group'
            Session().commit()

            return dict(
                success=success,
                msg=msg
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to add member to user group `%s`' % (
                    user_group.users_group_name,
                )
            )

    # permission check inside
    def remove_user_from_user_group(self, apiuser, usergroupid, userid):
        """
        Removes a user from a user group. If user is not in given group success will
        be `false`. This command can be executed only
        using api_key belonging to user with admin rights or an admin of given user group

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param usergroupid:
        :param userid:


        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "success":  True|False,  # depends on if member is in group
                      "msg": "removed member <username> from user group <groupname> |
                              User wasn't in group"
                    }
            error:  null

        """
        user = get_user_or_error(userid)
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this user group !
            _perms = ('usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))

        try:
            success = UserGroupModel().remove_user_from_group(user_group, user)
            msg = 'removed member `%s` from user group `%s`' % (
                user.username, user_group.users_group_name
            )
            msg = msg if success else "User wasn't in group"
            Session().commit()
            return dict(success=success, msg=msg)
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to remove member from user group `%s`' % (
                    user_group.users_group_name,
                )
            )

    # permission check inside
    def get_repo(self, apiuser, repoid):
        """
        Gets an existing repository by it's name or repository_id. Members will return
        either users_group or user associated to that repository. This command can be
        executed only using api_key belonging to user with admin
        rights or regular user that have at least read access to repository.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int

        OUTPUT::

          id : <id_given_in_input>
          result : {
            {
                "repo_id" :          "<repo_id>",
                "repo_name" :        "<reponame>"
                "repo_type" :        "<repo_type>",
                "clone_uri" :        "<clone_uri>",
                "enable_downloads":  "<bool>",
                "enable_locking":    "<bool>",
                "enable_statistics": "<bool>",
                "private":           "<bool>",
                "created_on" :       "<date_time_created>",
                "description" :      "<description>",
                "landing_rev":       "<landing_rev>",
                "last_changeset":    {
                                       "author":   "<full_author>",
                                       "date":     "<date_time_of_commit>",
                                       "message":  "<commit_message>",
                                       "raw_id":   "<raw_id>",
                                       "revision": "<numeric_revision>",
                                       "short_id": "<short_id>"
                                     }
                "owner":             "<repo_owner>",
                "fork_of":           "<name_of_fork_parent>",
                "members" :     [
                                  {
                                    "name":     "<username>",
                                    "type" :    "user",
                                    "permission" : "repository.(read|write|admin)"
                                  },
                                  …
                                  {
                                    "name":     "<usergroup name>",
                                    "type" :    "user_group",
                                    "permission" : "usergroup.(read|write|admin)"
                                  },
                                  …
                                ]
                 "followers":   [<user_obj>, ...]
                 ]
            }
          }
          error :  null

        """
        repo = get_repo_or_error(repoid)

        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo !
            perms = ('repository.admin', 'repository.write', 'repository.read')
            if not HasRepoPermissionAnyApi(*perms)(user=apiuser, repo_name=repo.repo_name):
                raise JSONRPCError('repository `%s` does not exist' % (repoid,))

        members = []
        followers = []
        for user in repo.repo_to_perm:
            perm = user.permission.permission_name
            user = user.user
            user_data = {
                'name': user.username,
                'type': "user",
                'permission': perm
            }
            members.append(user_data)

        for user_group in repo.users_group_to_perm:
            perm = user_group.permission.permission_name
            user_group = user_group.users_group
            user_group_data = {
                'name': user_group.users_group_name,
                'type': "user_group",
                'permission': perm
            }
            members.append(user_group_data)

        for user in repo.followers:
            followers.append(user.user.get_api_data())

        data = repo.get_api_data()
        data['members'] = members
        data['followers'] = followers
        return data

    # permission check inside
    def get_repos(self, apiuser):
        """
        Lists all existing repositories. This command can be executed only using
        api_key belonging to user with admin rights or regular user that have
        admin, write or read access to repository.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser

        OUTPUT::

            id : <id_given_in_input>
            result: [
                      {
                        "repo_id" :          "<repo_id>",
                        "repo_name" :        "<reponame>"
                        "repo_type" :        "<repo_type>",
                        "clone_uri" :        "<clone_uri>",
                        "private": :         "<bool>",
                        "created_on" :       "<datetimecreated>",
                        "description" :      "<description>",
                        "landing_rev":       "<landing_rev>",
                        "owner":             "<repo_owner>",
                        "fork_of":           "<name_of_fork_parent>",
                        "enable_downloads":  "<bool>",
                        "enable_locking":    "<bool>",
                        "enable_statistics": "<bool>",
                      },
                      …
                    ]
            error:  null
        """
        result = []
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            repos = RepoModel().get_all_user_repos(user=apiuser)
        else:
            repos = RepoModel().get_all()

        for repo in repos:
            result.append(repo.get_api_data())
        return result

    # permission check inside
    def get_repo_nodes(self, apiuser, repoid, revision, root_path,
                       ret_type=Optional('all')):
        """
        returns a list of nodes and it's children in a flat list for a given path
        at given revision. It's possible to specify ret_type to show only `files` or
        `dirs`.  This command can be executed only using api_key belonging to
        user with admin rights or regular user that have at least read access to repository.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param revision: revision for which listing should be done
        :type revision: str
        :param root_path: path from which start displaying
        :type root_path: str
        :param ret_type: return type 'all|files|dirs' nodes
        :type ret_type: Optional(str)


        OUTPUT::

            id : <id_given_in_input>
            result: [
                      {
                        "name" :        "<name>"
                        "type" :        "<type>",
                      },
                      …
                    ]
            error:  null
        """
        repo = get_repo_or_error(repoid)

        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo !
            perms = ('repository.admin', 'repository.write', 'repository.read')
            if not HasRepoPermissionAnyApi(*perms)(user=apiuser, repo_name=repo.repo_name):
                raise JSONRPCError('repository `%s` does not exist' % (repoid,))

        ret_type = Optional.extract(ret_type)
        _map = {}
        try:
            _d, _f = ScmModel().get_nodes(repo, revision, root_path,
                                          flat=False)
            _map = {
                'all': _d + _f,
                'files': _f,
                'dirs': _d,
            }
            return _map[ret_type]
        except KeyError:
            raise JSONRPCError('ret_type must be one of %s'
                               % (','.join(_map.keys())))
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to get repo: `%s` nodes' % repo.repo_name
            )

    @HasPermissionAnyDecorator('hg.admin', 'hg.create.repository')
    def create_repo(self, apiuser, repo_name, owner=Optional(OAttr('apiuser')),
                    repo_type=Optional('hg'), description=Optional(''),
                    private=Optional(False), clone_uri=Optional(None),
                    landing_rev=Optional('rev:tip'),
                    enable_statistics=Optional(False),
                    enable_locking=Optional(False),
                    enable_downloads=Optional(False),
                    copy_permissions=Optional(False)):
        """
        Creates a repository. If repository name contains "/", all needed repository
        groups will be created. For example "foo/bar/baz" will create groups
        "foo", "bar" (with "foo" as parent), and create "baz" repository with
        "bar" as group. This command can be executed only using api_key
        belonging to user with admin rights or regular user that have create
        repository permission. Regular users cannot specify owner parameter

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repo_name: repository name
        :type repo_name: str
        :param owner: user_id or username
        :type owner: Optional(str)
        :param repo_type: 'hg' or 'git'
        :type repo_type: Optional(str)
        :param description: repository description
        :type description: Optional(str)
        :param private:
        :type private: bool
        :param clone_uri:
        :type clone_uri: str
        :param landing_rev: <rev_type>:<rev>
        :type landing_rev: str
        :param enable_locking:
        :type enable_locking: bool
        :param enable_downloads:
        :type enable_downloads: bool
        :param enable_statistics:
        :type enable_statistics: bool
        :param copy_permissions: Copy permission from group that repository is
            beeing created.
        :type copy_permissions: bool

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg": "Created new repository `<reponame>`",
                      "success": true,
                      "task": "<celery task id or None if done sync>"
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
             'failed to create repository `<repo_name>`
          }

        """
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            if not isinstance(owner, Optional):
                #forbid setting owner for non-admins
                raise JSONRPCError(
                    'Only Kallithea admin can specify `owner` param'
                )
        if isinstance(owner, Optional):
            owner = apiuser.user_id

        owner = get_user_or_error(owner)

        if RepoModel().get_by_repo_name(repo_name):
            raise JSONRPCError("repo `%s` already exist" % repo_name)

        defs = Setting.get_default_repo_settings(strip_prefix=True)
        if isinstance(private, Optional):
            private = defs.get('repo_private') or Optional.extract(private)
        if isinstance(repo_type, Optional):
            repo_type = defs.get('repo_type')
        if isinstance(enable_statistics, Optional):
            enable_statistics = defs.get('repo_enable_statistics')
        if isinstance(enable_locking, Optional):
            enable_locking = defs.get('repo_enable_locking')
        if isinstance(enable_downloads, Optional):
            enable_downloads = defs.get('repo_enable_downloads')

        clone_uri = Optional.extract(clone_uri)
        description = Optional.extract(description)
        landing_rev = Optional.extract(landing_rev)
        copy_permissions = Optional.extract(copy_permissions)

        try:
            repo_name_cleaned = repo_name.split('/')[-1]
            # create structure of groups and return the last group
            repo_group = map_groups(repo_name)
            data = dict(
                repo_name=repo_name_cleaned,
                repo_name_full=repo_name,
                repo_type=repo_type,
                repo_description=description,
                owner=owner,
                repo_private=private,
                clone_uri=clone_uri,
                repo_group=repo_group,
                repo_landing_rev=landing_rev,
                enable_statistics=enable_statistics,
                enable_locking=enable_locking,
                enable_downloads=enable_downloads,
                repo_copy_permissions=copy_permissions,
            )

            task = RepoModel().create(form_data=data, cur_user=owner)
            from celery.result import BaseAsyncResult
            task_id = None
            if isinstance(task, BaseAsyncResult):
                task_id = task.task_id
            # no commit, it's done in RepoModel, or async via celery
            return dict(
                msg="Created new repository `%s`" % (repo_name,),
                success=True,  # cannot return the repo data here since fork
                               # cann be done async
                task=task_id
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to create repository `%s`' % (repo_name,))

    # permission check inside
    def update_repo(self, apiuser, repoid, name=Optional(None),
                    owner=Optional(OAttr('apiuser')),
                    group=Optional(None),
                    description=Optional(''), private=Optional(False),
                    clone_uri=Optional(None), landing_rev=Optional('rev:tip'),
                    enable_statistics=Optional(False),
                    enable_locking=Optional(False),
                    enable_downloads=Optional(False)):

        """
        Updates repo

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param name:
        :param owner:
        :param group:
        :param description:
        :param private:
        :param clone_uri:
        :param landing_rev:
        :param enable_statistics:
        :param enable_locking:
        :param enable_downloads:
        """
        repo = get_repo_or_error(repoid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo !
            if not HasRepoPermissionAnyApi('repository.admin')(user=apiuser,
                                                               repo_name=repo.repo_name):
                raise JSONRPCError('repository `%s` does not exist' % (repoid,))

        updates = {
            # update function requires this.
            'repo_name': repo.repo_name
        }
        repo_group = group
        if not isinstance(repo_group, Optional):
            repo_group = get_repo_group_or_error(repo_group)
            repo_group = repo_group.group_id
        try:
            store_update(updates, name, 'repo_name')
            store_update(updates, repo_group, 'repo_group')
            store_update(updates, owner, 'user')
            store_update(updates, description, 'repo_description')
            store_update(updates, private, 'repo_private')
            store_update(updates, clone_uri, 'clone_uri')
            store_update(updates, landing_rev, 'repo_landing_rev')
            store_update(updates, enable_statistics, 'repo_enable_statistics')
            store_update(updates, enable_locking, 'repo_enable_locking')
            store_update(updates, enable_downloads, 'repo_enable_downloads')

            RepoModel().update(repo, **updates)
            Session().commit()
            return dict(
                msg='updated repo ID:%s %s' % (repo.repo_id, repo.repo_name),
                repository=repo.get_api_data()
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to update repo `%s`' % repoid)

    @HasPermissionAnyDecorator('hg.admin', 'hg.fork.repository')
    def fork_repo(self, apiuser, repoid, fork_name,
                  owner=Optional(OAttr('apiuser')),
                  description=Optional(''), copy_permissions=Optional(False),
                  private=Optional(False), landing_rev=Optional('rev:tip')):
        """
        Creates a fork of given repo. In case of using celery this will
        immidiatelly return success message, while fork is going to be created
        asynchronous. This command can be executed only using api_key belonging to
        user with admin rights or regular user that have fork permission, and at least
        read access to forking repository. Regular users cannot specify owner parameter.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param fork_name:
        :param owner:
        :param description:
        :param copy_permissions:
        :param private:
        :param landing_rev:

        INPUT::

            id : <id_for_response>
            api_key : "<api_key>"
            args:     {
                        "repoid" :          "<reponame or repo_id>",
                        "fork_name":        "<forkname>",
                        "owner":            "<username or user_id = Optional(=apiuser)>",
                        "description":      "<description>",
                        "copy_permissions": "<bool>",
                        "private":          "<bool>",
                        "landing_rev":      "<landing_rev>"
                      }

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg": "Created fork of `<reponame>` as `<forkname>`",
                      "success": true,
                      "task": "<celery task id or None if done sync>"
                    }
            error:  null

        """
        repo = get_repo_or_error(repoid)
        repo_name = repo.repo_name

        _repo = RepoModel().get_by_repo_name(fork_name)
        if _repo:
            type_ = 'fork' if _repo.fork else 'repo'
            raise JSONRPCError("%s `%s` already exist" % (type_, fork_name))

        if HasPermissionAnyApi('hg.admin')(user=apiuser):
            pass
        elif HasRepoPermissionAnyApi('repository.admin',
                                     'repository.write',
                                     'repository.read')(user=apiuser,
                                                        repo_name=repo.repo_name):
            if not isinstance(owner, Optional):
                #forbid setting owner for non-admins
                raise JSONRPCError(
                    'Only Kallithea admin can specify `owner` param'
                )
        else:
            raise JSONRPCError('repository `%s` does not exist' % (repoid,))

        if isinstance(owner, Optional):
            owner = apiuser.user_id

        owner = get_user_or_error(owner)

        try:
            # create structure of groups and return the last group
            group = map_groups(fork_name)

            form_data = dict(
                repo_name=fork_name,
                repo_name_full=fork_name,
                repo_group=group,
                repo_type=repo.repo_type,
                description=Optional.extract(description),
                private=Optional.extract(private),
                copy_permissions=Optional.extract(copy_permissions),
                landing_rev=Optional.extract(landing_rev),
                update_after_clone=False,
                fork_parent_id=repo.repo_id,
            )
            task = RepoModel().create_fork(form_data, cur_user=owner)
            # no commit, it's done in RepoModel, or async via celery
            from celery.result import BaseAsyncResult
            task_id = None
            if isinstance(task, BaseAsyncResult):
                task_id = task.task_id
            return dict(
                msg='Created fork of `%s` as `%s`' % (repo.repo_name,
                                                      fork_name),
                success=True,  # cannot return the repo data here since fork
                               # cann be done async
                task=task_id
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to fork repository `%s` as `%s`' % (repo_name,
                                                            fork_name)
            )

    # permission check inside
    def delete_repo(self, apiuser, repoid, forks=Optional('')):
        """
        Deletes a repository. This command can be executed only using api_key belonging
        to user with admin rights or regular user that have admin access to repository.
        When `forks` param is set it's possible to detach or delete forks of deleting
        repository

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param forks: `detach` or `delete`, what do do with attached forks for repo
        :type forks: Optional(str)

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg": "Deleted repository `<reponame>`",
                      "success": true
                    }
            error:  null

        """
        repo = get_repo_or_error(repoid)

        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo !
            if not HasRepoPermissionAnyApi('repository.admin')(user=apiuser,
                                                           repo_name=repo.repo_name):
                raise JSONRPCError('repository `%s` does not exist' % (repoid,))

        try:
            handle_forks = Optional.extract(forks)
            _forks_msg = ''
            _forks = [f for f in repo.forks]
            if handle_forks == 'detach':
                _forks_msg = ' ' + 'Detached %s forks' % len(_forks)
            elif handle_forks == 'delete':
                _forks_msg = ' ' + 'Deleted %s forks' % len(_forks)
            elif _forks:
                raise JSONRPCError(
                    'Cannot delete `%s` it still contains attached forks' %
                    (repo.repo_name,)
                )

            RepoModel().delete(repo, forks=forks)
            Session().commit()
            return dict(
                msg='Deleted repository `%s`%s' % (repo.repo_name, _forks_msg),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to delete repository `%s`' % (repo.repo_name,)
            )

    @HasPermissionAllDecorator('hg.admin')
    def grant_user_permission(self, apiuser, repoid, userid, perm):
        """
        Grant permission for user on given repository, or update existing one
        if found. This command can be executed only using api_key belonging to user
        with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param userid:
        :param perm: (repository.(none|read|write|admin))
        :type perm: str

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "Granted perm: `<perm>` for user: `<username>` in repo: `<reponame>`",
                      "success": true
                    }
            error:  null
        """
        repo = get_repo_or_error(repoid)
        user = get_user_or_error(userid)
        perm = get_perm_or_error(perm)

        try:

            RepoModel().grant_user_permission(repo=repo, user=user, perm=perm)

            Session().commit()
            return dict(
                msg='Granted perm: `%s` for user: `%s` in repo: `%s`' % (
                    perm.permission_name, user.username, repo.repo_name
                ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user: `%s` in repo: `%s`' % (
                    userid, repoid
                )
            )

    @HasPermissionAllDecorator('hg.admin')
    def revoke_user_permission(self, apiuser, repoid, userid):
        """
        Revoke permission for user on given repository. This command can be executed
        only using api_key belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param userid:

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "Revoked perm for user: `<username>` in repo: `<reponame>`",
                      "success": true
                    }
            error:  null

        """

        repo = get_repo_or_error(repoid)
        user = get_user_or_error(userid)
        try:
            RepoModel().revoke_user_permission(repo=repo, user=user)
            Session().commit()
            return dict(
                msg='Revoked perm for user: `%s` in repo: `%s`' % (
                    user.username, repo.repo_name
                ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user: `%s` in repo: `%s`' % (
                    userid, repoid
                )
            )

    # permission check inside
    def grant_user_group_permission(self, apiuser, repoid, usergroupid, perm):
        """
        Grant permission for user group on given repository, or update
        existing one if found. This command can be executed only using
        api_key belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param usergroupid: id of usergroup
        :type usergroupid: str or int
        :param perm: (repository.(none|read|write|admin))
        :type perm: str

        OUTPUT::

          id : <id_given_in_input>
          result : {
            "msg" : "Granted perm: `<perm>` for group: `<usersgroupname>` in repo: `<reponame>`",
            "success": true

          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to edit permission for user group: `<usergroup>` in repo `<repo>`'
          }

        """
        repo = get_repo_or_error(repoid)
        perm = get_perm_or_error(perm)
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo !
            _perms = ('repository.admin',)
            if not HasRepoPermissionAnyApi(*_perms)(
                    user=apiuser, repo_name=repo.repo_name):
                raise JSONRPCError('repository `%s` does not exist' % (repoid,))

            # check if we have at least read permission for this user group !
            _perms = ('usergroup.read', 'usergroup.write', 'usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))

        try:
            RepoModel().grant_user_group_permission(
                repo=repo, group_name=user_group, perm=perm)

            Session().commit()
            return dict(
                msg='Granted perm: `%s` for user group: `%s` in '
                    'repo: `%s`' % (
                        perm.permission_name, user_group.users_group_name,
                        repo.repo_name
                    ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user group: `%s` in '
                'repo: `%s`' % (
                    usergroupid, repo.repo_name
                )
            )

    # permission check inside
    def revoke_user_group_permission(self, apiuser, repoid, usergroupid):
        """
        Revoke permission for user group on given repository. This command can be
        executed only using api_key belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repoid: repository name or repository id
        :type repoid: str or int
        :param usergroupid:

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "Revoked perm for group: `<usersgroupname>` in repo: `<reponame>`",
                      "success": true
                    }
            error:  null
        """
        repo = get_repo_or_error(repoid)
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo !
            _perms = ('repository.admin',)
            if not HasRepoPermissionAnyApi(*_perms)(
                    user=apiuser, repo_name=repo.repo_name):
                raise JSONRPCError('repository `%s` does not exist' % (repoid,))

            # check if we have at least read permission for this user group !
            _perms = ('usergroup.read', 'usergroup.write', 'usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError('user group `%s` does not exist' % (usergroupid,))

        try:
            RepoModel().revoke_user_group_permission(
                repo=repo, group_name=user_group)

            Session().commit()
            return dict(
                msg='Revoked perm for user group: `%s` in repo: `%s`' % (
                    user_group.users_group_name, repo.repo_name
                ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user group: `%s` in '
                'repo: `%s`' % (
                    user_group.users_group_name, repo.repo_name
                )
            )

    @HasPermissionAllDecorator('hg.admin')
    def get_repo_group(self, apiuser, repogroupid):
        """
        Returns given repo group together with permissions, and repositories
        inside the group

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repogroupid: id/name of repository group
        :type repogroupid: str or int
        """
        repo_group = get_repo_group_or_error(repogroupid)

        members = []
        for user in repo_group.repo_group_to_perm:
            perm = user.permission.permission_name
            user = user.user
            user_data = {
                'name': user.username,
                'type': "user",
                'permission': perm
            }
            members.append(user_data)

        for user_group in repo_group.users_group_to_perm:
            perm = user_group.permission.permission_name
            user_group = user_group.users_group
            user_group_data = {
                'name': user_group.users_group_name,
                'type': "user_group",
                'permission': perm
            }
            members.append(user_group_data)

        data = repo_group.get_api_data()
        data["members"] = members
        return data

    @HasPermissionAllDecorator('hg.admin')
    def get_repo_groups(self, apiuser):
        """
        Returns all repository groups

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        """
        result = []
        for repo_group in RepoGroupModel().get_all():
            result.append(repo_group.get_api_data())
        return result

    @HasPermissionAllDecorator('hg.admin')
    def create_repo_group(self, apiuser, group_name, description=Optional(''),
                          owner=Optional(OAttr('apiuser')),
                          parent=Optional(None),
                          copy_permissions=Optional(False)):
        """
        Creates a repository group. This command can be executed only using
        api_key belonging to user with admin rights.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param group_name:
        :type group_name:
        :param description:
        :type description:
        :param owner:
        :type owner:
        :param parent:
        :type parent:
        :param copy_permissions:
        :type copy_permissions:

        OUTPUT::

          id : <id_given_in_input>
          result : {
              "msg": "created new repo group `<repo_group_name>`"
              "repo_group": <repogroup_object>
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            failed to create repo group `<repogroupid>`
          }

        """
        if RepoGroup.get_by_group_name(group_name):
            raise JSONRPCError("repo group `%s` already exist" % (group_name,))

        if isinstance(owner, Optional):
            owner = apiuser.user_id
        group_description = Optional.extract(description)
        parent_group = Optional.extract(parent)
        if not isinstance(parent, Optional):
            parent_group = get_repo_group_or_error(parent_group)

        copy_permissions = Optional.extract(copy_permissions)
        try:
            repo_group = RepoGroupModel().create(
                group_name=group_name,
                group_description=group_description,
                owner=owner,
                parent=parent_group,
                copy_permissions=copy_permissions
            )
            Session().commit()
            return dict(
                msg='created new repo group `%s`' % group_name,
                repo_group=repo_group.get_api_data()
            )
        except Exception:

            log.error(traceback.format_exc())
            raise JSONRPCError('failed to create repo group `%s`' % (group_name,))

    @HasPermissionAllDecorator('hg.admin')
    def update_repo_group(self, apiuser, repogroupid, group_name=Optional(''),
                          description=Optional(''),
                          owner=Optional(OAttr('apiuser')),
                          parent=Optional(None), enable_locking=Optional(False)):
        repo_group = get_repo_group_or_error(repogroupid)

        updates = {}
        try:
            store_update(updates, group_name, 'group_name')
            store_update(updates, description, 'group_description')
            store_update(updates, owner, 'owner')
            store_update(updates, parent, 'parent_group')
            store_update(updates, enable_locking, 'enable_locking')
            repo_group = RepoGroupModel().update(repo_group, updates)
            Session().commit()
            return dict(
                msg='updated repository group ID:%s %s' % (repo_group.group_id,
                                                           repo_group.group_name),
                repo_group=repo_group.get_api_data()
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to update repository group `%s`'
                               % (repogroupid,))

    @HasPermissionAllDecorator('hg.admin')
    def delete_repo_group(self, apiuser, repogroupid):
        """

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repogroupid: name or id of repository group
        :type repogroupid: str or int

        OUTPUT::

          id : <id_given_in_input>
          result : {
            'msg': 'deleted repo group ID:<repogroupid> <repogroupname>
            'repo_group': null
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to delete repo group ID:<repogroupid> <repogroupname>"
          }

        """
        repo_group = get_repo_group_or_error(repogroupid)

        try:
            RepoGroupModel().delete(repo_group)
            Session().commit()
            return dict(
                msg='deleted repo group ID:%s %s' %
                    (repo_group.group_id, repo_group.group_name),
                repo_group=None
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to delete repo group ID:%s %s' %
                               (repo_group.group_id, repo_group.group_name)
            )

    # permission check inside
    def grant_user_permission_to_repo_group(self, apiuser, repogroupid, userid,
                                            perm, apply_to_children=Optional('none')):
        """
        Grant permission for user on given repository group, or update existing
        one if found. This command can be executed only using api_key belonging
        to user with admin rights, or user who has admin right to given repository
        group.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repogroupid: name or id of repository group
        :type repogroupid: str or int
        :param userid:
        :param perm: (group.(none|read|write|admin))
        :type perm: str
        :param apply_to_children: 'none', 'repos', 'groups', 'all'
        :type apply_to_children: str

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "Granted perm: `<perm>` (recursive:<apply_to_children>) for user: `<username>` in repo group: `<repo_group_name>`",
                      "success": true
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to edit permission for user: `<userid>` in repo group: `<repo_group_name>`"
          }

        """

        repo_group = get_repo_group_or_error(repogroupid)

        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo group !
            if not HasRepoGroupPermissionAnyApi('group.admin')(user=apiuser,
                                                               group_name=repo_group.group_name):
                raise JSONRPCError('repository group `%s` does not exist' % (repogroupid,))

        user = get_user_or_error(userid)
        perm = get_perm_or_error(perm, prefix='group.')
        apply_to_children = Optional.extract(apply_to_children)

        try:
            RepoGroupModel().add_permission(repo_group=repo_group,
                                            obj=user,
                                            obj_type="user",
                                            perm=perm,
                                            recursive=apply_to_children)
            Session().commit()
            return dict(
                msg='Granted perm: `%s` (recursive:%s) for user: `%s` in repo group: `%s`' % (
                    perm.permission_name, apply_to_children, user.username, repo_group.name
                ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user: `%s` in repo group: `%s`' % (
                    userid, repo_group.name))

    # permission check inside
    def revoke_user_permission_from_repo_group(self, apiuser, repogroupid, userid,
                                               apply_to_children=Optional('none')):
        """
        Revoke permission for user on given repository group. This command can
        be executed only using api_key belonging to user with admin rights, or
        user who has admin right to given repository group.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repogroupid: name or id of repository group
        :type repogroupid: str or int
        :param userid:
        :type userid:
        :param apply_to_children: 'none', 'repos', 'groups', 'all'
        :type apply_to_children: str

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "Revoked perm (recursive:<apply_to_children>) for user: `<username>` in repo group: `<repo_group_name>`",
                      "success": true
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to edit permission for user: `<userid>` in repo group: `<repo_group_name>`"
          }

        """

        repo_group = get_repo_group_or_error(repogroupid)

        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo group !
            if not HasRepoGroupPermissionAnyApi('group.admin')(user=apiuser,
                                                               group_name=repo_group.group_name):
                raise JSONRPCError('repository group `%s` does not exist' % (repogroupid,))

        user = get_user_or_error(userid)
        apply_to_children = Optional.extract(apply_to_children)

        try:
            RepoGroupModel().delete_permission(repo_group=repo_group,
                                               obj=user,
                                               obj_type="user",
                                               recursive=apply_to_children)

            Session().commit()
            return dict(
                msg='Revoked perm (recursive:%s) for user: `%s` in repo group: `%s`' % (
                    apply_to_children, user.username, repo_group.name
                ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user: `%s` in repo group: `%s`' % (
                    userid, repo_group.name))

    # permission check inside
    def grant_user_group_permission_to_repo_group(
            self, apiuser, repogroupid, usergroupid, perm,
            apply_to_children=Optional('none'),):
        """
        Grant permission for user group on given repository group, or update
        existing one if found. This command can be executed only using
        api_key belonging to user with admin rights, or user who has admin
        right to given repository group.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repogroupid: name or id of repository group
        :type repogroupid: str or int
        :param usergroupid: id of usergroup
        :type usergroupid: str or int
        :param perm: (group.(none|read|write|admin))
        :type perm: str
        :param apply_to_children: 'none', 'repos', 'groups', 'all'
        :type apply_to_children: str

        OUTPUT::

          id : <id_given_in_input>
          result : {
            "msg" : "Granted perm: `<perm>` (recursive:<apply_to_children>) for user group: `<usersgroupname>` in repo group: `<repo_group_name>`",
            "success": true

          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to edit permission for user group: `<usergroup>` in repo group: `<repo_group_name>`"
          }

        """
        repo_group = get_repo_group_or_error(repogroupid)
        perm = get_perm_or_error(perm, prefix='group.')
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo group !
            _perms = ('group.admin',)
            if not HasRepoGroupPermissionAnyApi(*_perms)(
                    user=apiuser, group_name=repo_group.group_name):
                raise JSONRPCError(
                    'repository group `%s` does not exist' % (repogroupid,))

            # check if we have at least read permission for this user group !
            _perms = ('usergroup.read', 'usergroup.write', 'usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError(
                    'user group `%s` does not exist' % (usergroupid,))

        apply_to_children = Optional.extract(apply_to_children)

        try:
            RepoGroupModel().add_permission(repo_group=repo_group,
                                            obj=user_group,
                                            obj_type="user_group",
                                            perm=perm,
                                            recursive=apply_to_children)
            Session().commit()
            return dict(
                msg='Granted perm: `%s` (recursive:%s) for user group: `%s` in repo group: `%s`' % (
                        perm.permission_name, apply_to_children,
                        user_group.users_group_name, repo_group.name
                    ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user group: `%s` in '
                'repo group: `%s`' % (
                    usergroupid, repo_group.name
                )
            )

    # permission check inside
    def revoke_user_group_permission_from_repo_group(
            self, apiuser, repogroupid, usergroupid,
            apply_to_children=Optional('none')):
        """
        Revoke permission for user group on given repository. This command can be
        executed only using api_key belonging to user with admin rights, or
        user who has admin right to given repository group.

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param repogroupid: name or id of repository group
        :type repogroupid: str or int
        :param usergroupid:
        :param apply_to_children: 'none', 'repos', 'groups', 'all'
        :type apply_to_children: str

        OUTPUT::

            id : <id_given_in_input>
            result: {
                      "msg" : "Revoked perm (recursive:<apply_to_children>) for user group: `<usersgroupname>` in repo group: `<repo_group_name>`",
                      "success": true
                    }
            error:  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to edit permission for user group: `<usergroup>` in repo group: `<repo_group_name>`"
          }


        """
        repo_group = get_repo_group_or_error(repogroupid)
        user_group = get_user_group_or_error(usergroupid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # check if we have admin permission for this repo group !
            _perms = ('group.admin',)
            if not HasRepoGroupPermissionAnyApi(*_perms)(
                    user=apiuser, group_name=repo_group.group_name):
                raise JSONRPCError(
                    'repository group `%s` does not exist' % (repogroupid,))

            # check if we have at least read permission for this user group !
            _perms = ('usergroup.read', 'usergroup.write', 'usergroup.admin',)
            if not HasUserGroupPermissionAny(*_perms)(
                    user=apiuser, user_group_name=user_group.users_group_name):
                raise JSONRPCError(
                    'user group `%s` does not exist' % (usergroupid,))

        apply_to_children = Optional.extract(apply_to_children)

        try:
            RepoGroupModel().delete_permission(repo_group=repo_group,
                                               obj=user_group,
                                               obj_type="user_group",
                                               recursive=apply_to_children)
            Session().commit()
            return dict(
                msg='Revoked perm (recursive:%s) for user group: `%s` in repo group: `%s`' % (
                    apply_to_children, user_group.users_group_name, repo_group.name
                ),
                success=True
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError(
                'failed to edit permission for user group: `%s` in repo group: `%s`' % (
                    user_group.users_group_name, repo_group.name
                )
            )

    def get_gist(self, apiuser, gistid):
        """
        Get given gist by id

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param gistid: id of private or public gist
        :type gistid: str
        """
        gist = get_gist_or_error(gistid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            if gist.gist_owner != apiuser.user_id:
                raise JSONRPCError('gist `%s` does not exist' % (gistid,))
        return gist.get_api_data()

    def get_gists(self, apiuser, userid=Optional(OAttr('apiuser'))):
        """
        Get all gists for given user. If userid is empty returned gists
        are for user who called the api

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param userid: user to get gists for
        :type userid: Optional(str or int)
        """
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            # make sure normal user does not pass someone else userid,
            # he is not allowed to do that
            if not isinstance(userid, Optional) and userid != apiuser.user_id:
                raise JSONRPCError(
                    'userid is not the same as your user'
                )

        if isinstance(userid, Optional):
            user_id = apiuser.user_id
        else:
            user_id = get_user_or_error(userid).user_id

        gists = []
        _gists = Gist().query()\
            .filter(or_(Gist.gist_expires == -1, Gist.gist_expires >= time.time()))\
            .filter(Gist.gist_owner == user_id)\
            .order_by(Gist.created_on.desc())
        for gist in _gists:
            gists.append(gist.get_api_data())
        return gists

    def create_gist(self, apiuser, files, owner=Optional(OAttr('apiuser')),
                    gist_type=Optional(Gist.GIST_PUBLIC), lifetime=Optional(-1),
                    description=Optional('')):

        """
        Creates new Gist

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param files: files to be added to gist
            {'filename': {'content':'...', 'lexer': null},
             'filename2': {'content':'...', 'lexer': null}}
        :type files: dict
        :param owner: gist owner, defaults to api method caller
        :type owner: Optional(str or int)
        :param gist_type: type of gist 'public' or 'private'
        :type gist_type: Optional(str)
        :param lifetime: time in minutes of gist lifetime
        :type lifetime: Optional(int)
        :param description: gist description
        :type description: Optional(str)

        OUTPUT::

          id : <id_given_in_input>
          result : {
            "msg": "created new gist",
            "gist": {}
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to create gist"
          }

        """
        try:
            if isinstance(owner, Optional):
                owner = apiuser.user_id

            owner = get_user_or_error(owner)
            description = Optional.extract(description)
            gist_type = Optional.extract(gist_type)
            lifetime = Optional.extract(lifetime)

            gist = GistModel().create(description=description,
                                      owner=owner,
                                      gist_mapping=files,
                                      gist_type=gist_type,
                                      lifetime=lifetime)
            Session().commit()
            return dict(
                msg='created new gist',
                gist=gist.get_api_data()
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to create gist')

    # def update_gist(self, apiuser, gistid, files, owner=Optional(OAttr('apiuser')),
    #                 gist_type=Optional(Gist.GIST_PUBLIC),
    #                 gist_lifetime=Optional(-1), gist_description=Optional('')):
    #     gist = get_gist_or_error(gistid)
    #     updates = {}

    # permission check inside
    def delete_gist(self, apiuser, gistid):
        """
        Deletes existing gist

        :param apiuser: filled automatically from apikey
        :type apiuser: AuthUser
        :param gistid: id of gist to delete
        :type gistid: str

        OUTPUT::

          id : <id_given_in_input>
          result : {
            "deleted gist ID: <gist_id>",
            "gist": null
          }
          error :  null

        ERROR OUTPUT::

          id : <id_given_in_input>
          result : null
          error :  {
            "failed to delete gist ID:<gist_id>"
          }

        """
        gist = get_gist_or_error(gistid)
        if not HasPermissionAnyApi('hg.admin')(user=apiuser):
            if gist.gist_owner != apiuser.user_id:
                raise JSONRPCError('gist `%s` does not exist' % (gistid,))

        try:
            GistModel().delete(gist)
            Session().commit()
            return dict(
                msg='deleted gist ID:%s' % (gist.gist_access_id,),
                gist=None
            )
        except Exception:
            log.error(traceback.format_exc())
            raise JSONRPCError('failed to delete gist ID:%s'
                               % (gist.gist_access_id,))
