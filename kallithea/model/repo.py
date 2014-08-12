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
kallithea.model.repo
~~~~~~~~~~~~~~~~~~~~

Repository model for kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jun 5, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""

from __future__ import with_statement
import os
import shutil
import logging
import traceback
from datetime import datetime
from kallithea.lib.utils import make_ui

from kallithea.lib.vcs.backends import get_backend
from kallithea.lib.compat import json
from kallithea.lib.utils2 import LazyProperty, safe_str, safe_unicode, \
    remove_prefix, obfuscate_url_pw, get_current_authuser
from kallithea.lib.caching_query import FromCache
from kallithea.lib.hooks import log_delete_repository

from kallithea.model import BaseModel
from kallithea.model.db import Repository, UserRepoToPerm, UserGroupRepoToPerm, \
    UserRepoGroupToPerm, UserGroupRepoGroupToPerm, User, Permission, \
    Statistics, UserGroup, Ui, RepoGroup, \
    Setting, RepositoryField

from kallithea.lib import helpers as h
from kallithea.lib.auth import HasRepoPermissionAny, HasUserGroupPermissionAny
from kallithea.lib.exceptions import AttachedForksError
from kallithea.model.scm import UserGroupList

log = logging.getLogger(__name__)


class RepoModel(BaseModel):

    cls = Repository
    URL_SEPARATOR = Repository.url_sep()

    def _get_user_group(self, users_group):
        return self._get_instance(UserGroup, users_group,
                                  callback=UserGroup.get_by_group_name)

    def _get_repo_group(self, repo_group):
        return self._get_instance(RepoGroup, repo_group,
                                  callback=RepoGroup.get_by_group_name)

    def _create_default_perms(self, repository, private):
        # create default permission
        default = 'repository.read'
        def_user = User.get_default_user()
        for p in def_user.user_perms:
            if p.permission.permission_name.startswith('repository.'):
                default = p.permission.permission_name
                break

        default_perm = 'repository.none' if private else default

        repo_to_perm = UserRepoToPerm()
        repo_to_perm.permission = Permission.get_by_key(default_perm)

        repo_to_perm.repository = repository
        repo_to_perm.user_id = def_user.user_id

        return repo_to_perm

    @LazyProperty
    def repos_path(self):
        """
        Gets the repositories root path from database
        """

        q = self.sa.query(Ui).filter(Ui.ui_key == '/').one()
        return q.ui_value

    def get(self, repo_id, cache=False):
        repo = self.sa.query(Repository) \
            .filter(Repository.repo_id == repo_id)

        if cache:
            repo = repo.options(FromCache("sql_cache_short",
                                          "get_repo_%s" % repo_id))
        return repo.scalar()

    def get_repo(self, repository):
        return self._get_repo(repository)

    def get_by_repo_name(self, repo_name, cache=False):
        repo = self.sa.query(Repository) \
            .filter(Repository.repo_name == repo_name)

        if cache:
            repo = repo.options(FromCache("sql_cache_short",
                                          "get_repo_%s" % repo_name))
        return repo.scalar()

    def get_all_user_repos(self, user):
        """
        Gets all repositories that user have at least read access

        :param user:
        """
        from kallithea.lib.auth import AuthUser
        user = self._get_user(user)
        repos = AuthUser(user_id=user.user_id).permissions['repositories']
        access_check = lambda r: r[1] in ['repository.read',
                                          'repository.write',
                                          'repository.admin']
        repos = [x[0] for x in filter(access_check, repos.items())]
        return Repository.query().filter(Repository.repo_name.in_(repos))

    def get_users_js(self):
        users = self.sa.query(User).filter(User.active == True).all()
        return json.dumps([
            {
                'id': u.user_id,
                'fname': u.name,
                'lname': u.lastname,
                'nname': u.username,
                'gravatar_lnk': h.gravatar_url(u.email, 14)
            } for u in users]
        )

    def get_user_groups_js(self):
        user_groups = self.sa.query(UserGroup) \
            .filter(UserGroup.users_group_active == True).all()
        user_groups = UserGroupList(user_groups, perm_set=['usergroup.read',
                                                           'usergroup.write',
                                                           'usergroup.admin'])
        return json.dumps([
            {
                'id': gr.users_group_id,
                'grname': gr.users_group_name,
                'grmembers': len(gr.members),
            } for gr in user_groups]
        )

    @classmethod
    def _render_datatable(cls, tmpl, *args, **kwargs):
        import kallithea
        from pylons import tmpl_context as c
        from pylons.i18n.translation import _

        _tmpl_lookup = kallithea.CONFIG['pylons.app_globals'].mako_lookup
        template = _tmpl_lookup.get_template('data_table/_dt_elements.html')

        tmpl = template.get_def(tmpl)
        kwargs.update(dict(_=_, h=h, c=c))
        return tmpl.render(*args, **kwargs)

    @classmethod
    def update_repoinfo(cls, repositories=None):
        if not repositories:
            repositories = Repository.getAll()
        for repo in repositories:
            repo.update_changeset_cache()

    def get_repos_as_dict(self, repos_list=None, admin=False, perm_check=True,
                          super_user_actions=False):
        _render = self._render_datatable
        from pylons import tmpl_context as c

        def quick_menu(repo_name):
            return _render('quick_menu', repo_name)

        def repo_lnk(name, rtype, rstate, private, fork_of):
            return _render('repo_name', name, rtype, rstate, private, fork_of,
                           short_name=not admin, admin=False)

        def last_change(last_change):
            return _render("last_change", last_change)

        def rss_lnk(repo_name):
            return _render("rss", repo_name)

        def atom_lnk(repo_name):
            return _render("atom", repo_name)

        def last_rev(repo_name, cs_cache):
            return _render('revision', repo_name, cs_cache.get('revision'),
                           cs_cache.get('raw_id'), cs_cache.get('author'),
                           cs_cache.get('message'))

        def desc(desc):
            if c.visual.stylify_metatags:
                return h.urlify_text(h.desc_stylize(h.truncate(desc, 60)))
            else:
                return h.urlify_text(h.truncate(desc, 60))

        def state(repo_state):
            return _render("repo_state", repo_state)

        def repo_actions(repo_name):
            return _render('repo_actions', repo_name, super_user_actions)

        def owner_actions(user_id, username):
            return _render('user_name', user_id, username)

        repos_data = []
        for repo in repos_list:
            if perm_check:
                # check permission at this level
                if not HasRepoPermissionAny(
                        'repository.read', 'repository.write',
                        'repository.admin'
                )(repo.repo_name, 'get_repos_as_dict check'):
                    continue
            cs_cache = repo.changeset_cache
            row = {
                "menu": quick_menu(repo.repo_name),
                "raw_name": repo.repo_name.lower(),
                "name": repo_lnk(repo.repo_name, repo.repo_type,
                                 repo.repo_state, repo.private, repo.fork),
                "last_change": last_change(repo.last_db_change),
                "last_changeset": last_rev(repo.repo_name, cs_cache),
                "last_rev_raw": cs_cache.get('revision'),
                "desc": desc(repo.description),
                "owner": h.person(repo.user.username),
                "state": state(repo.repo_state),
                "rss": rss_lnk(repo.repo_name),
                "atom": atom_lnk(repo.repo_name),

            }
            if admin:
                row.update({
                    "action": repo_actions(repo.repo_name),
                    "owner": owner_actions(repo.user.user_id,
                                           h.person(repo.user.username))
                })
            repos_data.append(row)

        return {
            "totalRecords": len(repos_list),
            "startIndex": 0,
            "sort": "name",
            "dir": "asc",
            "records": repos_data
        }

    def _get_defaults(self, repo_name):
        """
        Gets information about repository, and returns a dict for
        usage in forms

        :param repo_name:
        """

        repo_info = Repository.get_by_repo_name(repo_name)

        if repo_info is None:
            return None

        defaults = repo_info.get_dict()
        group, repo_name, repo_name_full = repo_info.groups_and_repo
        defaults['repo_name'] = repo_name
        defaults['repo_group'] = getattr(group[-1] if group else None,
                                         'group_id', None)

        for strip, k in [(0, 'repo_type'), (1, 'repo_enable_downloads'),
                         (1, 'repo_description'), (1, 'repo_enable_locking'),
                         (1, 'repo_landing_rev'), (0, 'clone_uri'),
                         (1, 'repo_private'), (1, 'repo_enable_statistics')]:
            attr = k
            if strip:
                attr = remove_prefix(k, 'repo_')

            val = defaults[attr]
            if k == 'repo_landing_rev':
                val = ':'.join(defaults[attr])
            defaults[k] = val
            if k == 'clone_uri':
                defaults['clone_uri_hidden'] = repo_info.clone_uri_hidden

        # fill owner
        if repo_info.user:
            defaults.update({'user': repo_info.user.username})
        else:
            replacement_user = User.query().filter(User.admin ==
                                                   True).first().username
            defaults.update({'user': replacement_user})

        # fill repository users
        for p in repo_info.repo_to_perm:
            defaults.update({'u_perm_%s' % p.user.username:
                                 p.permission.permission_name})

        # fill repository groups
        for p in repo_info.users_group_to_perm:
            defaults.update({'g_perm_%s' % p.users_group.users_group_name:
                                 p.permission.permission_name})

        return defaults

    def update(self, repo, **kwargs):
        try:
            cur_repo = self._get_repo(repo)
            org_repo_name = cur_repo.repo_name
            if 'user' in kwargs:
                cur_repo.user = User.get_by_username(kwargs['user'])

            if 'repo_group' in kwargs:
                cur_repo.group = RepoGroup.get(kwargs['repo_group'])
            log.debug('Updating repo %s with params:%s' % (cur_repo, kwargs))
            for strip, k in [(1, 'repo_enable_downloads'),
                             (1, 'repo_description'),
                             (1, 'repo_enable_locking'),
                             (1, 'repo_landing_rev'),
                             (1, 'repo_private'),
                             (1, 'repo_enable_statistics'),
                             (0, 'clone_uri'),]:
                if k in kwargs:
                    val = kwargs[k]
                    if strip:
                        k = remove_prefix(k, 'repo_')
                    if k == 'clone_uri':
                        from kallithea.model.validators import Missing
                        _change = kwargs.get('clone_uri_change')
                        if _change == Missing:
                            # we don't change the value, so use original one
                            val = cur_repo.clone_uri

                    setattr(cur_repo, k, val)

            new_name = cur_repo.get_new_name(kwargs['repo_name'])
            cur_repo.repo_name = new_name
            #if private flag is set, reset default permission to NONE

            if kwargs.get('repo_private'):
                EMPTY_PERM = 'repository.none'
                RepoModel().grant_user_permission(
                    repo=cur_repo, user='default', perm=EMPTY_PERM
                )
                #handle extra fields
            for field in filter(lambda k: k.startswith(RepositoryField.PREFIX),
                                kwargs):
                k = RepositoryField.un_prefix_key(field)
                ex_field = RepositoryField.get_by_key_name(key=k, repo=cur_repo)
                if ex_field:
                    ex_field.field_value = kwargs[field]
                    self.sa.add(ex_field)
            self.sa.add(cur_repo)

            if org_repo_name != new_name:
                # rename repository
                self._rename_filesystem_repo(old=org_repo_name, new=new_name)

            return cur_repo
        except Exception:
            log.error(traceback.format_exc())
            raise

    def _create_repo(self, repo_name, repo_type, description, owner,
                     private=False, clone_uri=None, repo_group=None,
                     landing_rev='rev:tip', fork_of=None,
                     copy_fork_permissions=False, enable_statistics=False,
                     enable_locking=False, enable_downloads=False,
                     copy_group_permissions=False, state=Repository.STATE_PENDING):
        """
        Create repository inside database with PENDING state, this should be
        only executed by create() repo. With exception of importing existing repos

        """
        from kallithea.model.scm import ScmModel

        owner = self._get_user(owner)
        fork_of = self._get_repo(fork_of)
        repo_group = self._get_repo_group(repo_group)
        try:
            repo_name = safe_unicode(repo_name)
            description = safe_unicode(description)
            # repo name is just a name of repository
            # while repo_name_full is a full qualified name that is combined
            # with name and path of group
            repo_name_full = repo_name
            repo_name = repo_name.split(self.URL_SEPARATOR)[-1]

            new_repo = Repository()
            new_repo.repo_state = state
            new_repo.enable_statistics = False
            new_repo.repo_name = repo_name_full
            new_repo.repo_type = repo_type
            new_repo.user = owner
            new_repo.group = repo_group
            new_repo.description = description or repo_name
            new_repo.private = private
            new_repo.clone_uri = clone_uri
            new_repo.landing_rev = landing_rev

            new_repo.enable_statistics = enable_statistics
            new_repo.enable_locking = enable_locking
            new_repo.enable_downloads = enable_downloads

            if repo_group:
                new_repo.enable_locking = repo_group.enable_locking

            if fork_of:
                parent_repo = fork_of
                new_repo.fork = parent_repo

            self.sa.add(new_repo)

            if fork_of and copy_fork_permissions:
                repo = fork_of
                user_perms = UserRepoToPerm.query() \
                    .filter(UserRepoToPerm.repository == repo).all()
                group_perms = UserGroupRepoToPerm.query() \
                    .filter(UserGroupRepoToPerm.repository == repo).all()

                for perm in user_perms:
                    UserRepoToPerm.create(perm.user, new_repo, perm.permission)

                for perm in group_perms:
                    UserGroupRepoToPerm.create(perm.users_group, new_repo,
                                               perm.permission)

            elif repo_group and copy_group_permissions:

                user_perms = UserRepoGroupToPerm.query() \
                    .filter(UserRepoGroupToPerm.group == repo_group).all()

                group_perms = UserGroupRepoGroupToPerm.query() \
                    .filter(UserGroupRepoGroupToPerm.group == repo_group).all()

                for perm in user_perms:
                    perm_name = perm.permission.permission_name.replace('group.', 'repository.')
                    perm_obj = Permission.get_by_key(perm_name)
                    UserRepoToPerm.create(perm.user, new_repo, perm_obj)

                for perm in group_perms:
                    perm_name = perm.permission.permission_name.replace('group.', 'repository.')
                    perm_obj = Permission.get_by_key(perm_name)
                    UserGroupRepoToPerm.create(perm.users_group, new_repo, perm_obj)

            else:
                perm_obj = self._create_default_perms(new_repo, private)
                self.sa.add(perm_obj)

            # now automatically start following this repository as owner
            ScmModel(self.sa).toggle_following_repo(new_repo.repo_id,
                                                    owner.user_id)
            # we need to flush here, in order to check if database won't
            # throw any exceptions, create filesystem dirs at the very end
            self.sa.flush()
            return new_repo
        except Exception:
            log.error(traceback.format_exc())
            raise

    def create(self, form_data, cur_user):
        """
        Create repository using celery tasks

        :param form_data:
        :param cur_user:
        """
        from kallithea.lib.celerylib import tasks, run_task
        return run_task(tasks.create_repo, form_data, cur_user)

    def _update_permissions(self, repo, perms_new=None, perms_updates=None,
                            check_perms=True):
        if not perms_new:
            perms_new = []
        if not perms_updates:
            perms_updates = []

        # update permissions
        for member, perm, member_type in perms_updates:
            if member_type == 'user':
                # this updates existing one
                self.grant_user_permission(
                    repo=repo, user=member, perm=perm
                )
            else:
                #check if we have permissions to alter this usergroup
                req_perms = (
                    'usergroup.read', 'usergroup.write', 'usergroup.admin')
                if not check_perms or HasUserGroupPermissionAny(*req_perms)(
                        member):
                    self.grant_user_group_permission(
                        repo=repo, group_name=member, perm=perm
                    )
            # set new permissions
        for member, perm, member_type in perms_new:
            if member_type == 'user':
                self.grant_user_permission(
                    repo=repo, user=member, perm=perm
                )
            else:
                #check if we have permissions to alter this usergroup
                req_perms = (
                    'usergroup.read', 'usergroup.write', 'usergroup.admin')
                if not check_perms or HasUserGroupPermissionAny(*req_perms)(
                        member):
                    self.grant_user_group_permission(
                        repo=repo, group_name=member, perm=perm
                    )

    def create_fork(self, form_data, cur_user):
        """
        Simple wrapper into executing celery task for fork creation

        :param form_data:
        :param cur_user:
        """
        from kallithea.lib.celerylib import tasks, run_task
        return run_task(tasks.create_repo_fork, form_data, cur_user)

    def delete(self, repo, forks=None, fs_remove=True, cur_user=None):
        """
        Delete given repository, forks parameter defines what do do with
        attached forks. Throws AttachedForksError if deleted repo has attached
        forks

        :param repo:
        :param forks: str 'delete' or 'detach'
        :param fs_remove: remove(archive) repo from filesystem
        """
        if not cur_user:
            cur_user = getattr(get_current_authuser(), 'username', None)
        repo = self._get_repo(repo)
        if repo:
            if forks == 'detach':
                for r in repo.forks:
                    r.fork = None
                    self.sa.add(r)
            elif forks == 'delete':
                for r in repo.forks:
                    self.delete(r, forks='delete')
            elif [f for f in repo.forks]:
                raise AttachedForksError()

            old_repo_dict = repo.get_dict()
            try:
                self.sa.delete(repo)
                if fs_remove:
                    self._delete_filesystem_repo(repo)
                else:
                    log.debug('skipping removal from filesystem')
                log_delete_repository(old_repo_dict,
                                      deleted_by=cur_user)
            except Exception:
                log.error(traceback.format_exc())
                raise

    def grant_user_permission(self, repo, user, perm):
        """
        Grant permission for user on given repository, or update existing one
        if found

        :param repo: Instance of Repository, repository_id, or repository name
        :param user: Instance of User, user_id or username
        :param perm: Instance of Permission, or permission_name
        """
        user = self._get_user(user)
        repo = self._get_repo(repo)
        permission = self._get_perm(perm)

        # check if we have that permission already
        obj = self.sa.query(UserRepoToPerm) \
            .filter(UserRepoToPerm.user == user) \
            .filter(UserRepoToPerm.repository == repo) \
            .scalar()
        if obj is None:
            # create new !
            obj = UserRepoToPerm()
        obj.repository = repo
        obj.user = user
        obj.permission = permission
        self.sa.add(obj)
        log.debug('Granted perm %s to %s on %s' % (perm, user, repo))
        return obj

    def revoke_user_permission(self, repo, user):
        """
        Revoke permission for user on given repository

        :param repo: Instance of Repository, repository_id, or repository name
        :param user: Instance of User, user_id or username
        """

        user = self._get_user(user)
        repo = self._get_repo(repo)

        obj = self.sa.query(UserRepoToPerm) \
            .filter(UserRepoToPerm.repository == repo) \
            .filter(UserRepoToPerm.user == user) \
            .scalar()
        if obj:
            self.sa.delete(obj)
            log.debug('Revoked perm on %s on %s' % (repo, user))

    def grant_user_group_permission(self, repo, group_name, perm):
        """
        Grant permission for user group on given repository, or update
        existing one if found

        :param repo: Instance of Repository, repository_id, or repository name
        :param group_name: Instance of UserGroup, users_group_id,
            or user group name
        :param perm: Instance of Permission, or permission_name
        """
        repo = self._get_repo(repo)
        group_name = self._get_user_group(group_name)
        permission = self._get_perm(perm)

        # check if we have that permission already
        obj = self.sa.query(UserGroupRepoToPerm) \
            .filter(UserGroupRepoToPerm.users_group == group_name) \
            .filter(UserGroupRepoToPerm.repository == repo) \
            .scalar()

        if obj is None:
            # create new
            obj = UserGroupRepoToPerm()

        obj.repository = repo
        obj.users_group = group_name
        obj.permission = permission
        self.sa.add(obj)
        log.debug('Granted perm %s to %s on %s' % (perm, group_name, repo))
        return obj

    def revoke_user_group_permission(self, repo, group_name):
        """
        Revoke permission for user group on given repository

        :param repo: Instance of Repository, repository_id, or repository name
        :param group_name: Instance of UserGroup, users_group_id,
            or user group name
        """
        repo = self._get_repo(repo)
        group_name = self._get_user_group(group_name)

        obj = self.sa.query(UserGroupRepoToPerm) \
            .filter(UserGroupRepoToPerm.repository == repo) \
            .filter(UserGroupRepoToPerm.users_group == group_name) \
            .scalar()
        if obj:
            self.sa.delete(obj)
            log.debug('Revoked perm to %s on %s' % (repo, group_name))

    def delete_stats(self, repo_name):
        """
        removes stats for given repo

        :param repo_name:
        """
        repo = self._get_repo(repo_name)
        try:
            obj = self.sa.query(Statistics) \
                .filter(Statistics.repository == repo).scalar()
            if obj:
                self.sa.delete(obj)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def _create_filesystem_repo(self, repo_name, repo_type, repo_group,
                                clone_uri=None, repo_store_location=None):
        """
        makes repository on filesystem. It's group aware means it'll create
        a repository within a group, and alter the paths accordingly of
        group location

        :param repo_name:
        :param alias:
        :param parent:
        :param clone_uri:
        :param repo_store_location:
        """
        from kallithea.lib.utils import is_valid_repo, is_valid_repo_group
        from kallithea.model.scm import ScmModel

        if '/' in repo_name:
            raise ValueError('repo_name must not contain groups got `%s`' % repo_name)

        if isinstance(repo_group, RepoGroup):
            new_parent_path = os.sep.join(repo_group.full_path_splitted)
        else:
            new_parent_path = repo_group or ''

        if repo_store_location:
            _paths = [repo_store_location]
        else:
            _paths = [self.repos_path, new_parent_path, repo_name]
            # we need to make it str for mercurial
        repo_path = os.path.join(*map(lambda x: safe_str(x), _paths))

        # check if this path is not a repository
        if is_valid_repo(repo_path, self.repos_path):
            raise Exception('This path %s is a valid repository' % repo_path)

        # check if this path is a group
        if is_valid_repo_group(repo_path, self.repos_path):
            raise Exception('This path %s is a valid group' % repo_path)

        log.info('creating repo %s in %s from url: `%s`' % (
            repo_name, safe_unicode(repo_path),
            obfuscate_url_pw(clone_uri)))

        backend = get_backend(repo_type)

        if repo_type == 'hg':
            baseui = make_ui('db', clear_session=False)
            # patch and reset hooks section of UI config to not run any
            # hooks on creating remote repo
            for k, v in baseui.configitems('hooks'):
                baseui.setconfig('hooks', k, None)

            repo = backend(repo_path, create=True, src_url=clone_uri, baseui=baseui)
        elif repo_type == 'git':
            repo = backend(repo_path, create=True, src_url=clone_uri, bare=True)
            # add kallithea hook into this repo
            ScmModel().install_git_hook(repo=repo)
        else:
            raise Exception('Not supported repo_type %s expected hg/git' % repo_type)

        log.debug('Created repo %s with %s backend'
                  % (safe_unicode(repo_name), safe_unicode(repo_type)))
        return repo

    def _rename_filesystem_repo(self, old, new):
        """
        renames repository on filesystem

        :param old: old name
        :param new: new name
        """
        log.info('renaming repo from %s to %s' % (old, new))

        old_path = os.path.join(self.repos_path, old)
        new_path = os.path.join(self.repos_path, new)
        if os.path.isdir(new_path):
            raise Exception(
                'Was trying to rename to already existing dir %s' % new_path
            )
        shutil.move(old_path, new_path)

    def _delete_filesystem_repo(self, repo):
        """
        removes repo from filesystem, the removal is actually done by
        renaming dir to a 'rm__*' prefix which Kallithea will skip.
        It can be undeleted later by reverting the rename.

        :param repo: repo object
        """
        rm_path = os.path.join(self.repos_path, repo.repo_name)
        log.info("Removing %s" % (rm_path))

        _now = datetime.now()
        _ms = str(_now.microsecond).rjust(6, '0')
        _d = 'rm__%s__%s' % (_now.strftime('%Y%m%d_%H%M%S_' + _ms),
                             repo.just_name)
        if repo.group:
            args = repo.group.full_path_splitted + [_d]
            _d = os.path.join(*args)
        shutil.move(rm_path, os.path.join(self.repos_path, _d))
