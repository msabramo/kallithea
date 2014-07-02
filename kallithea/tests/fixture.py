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
Helpers for fixture generation
"""
import os
import time
from kallithea.tests import *
from kallithea.model.db import Repository, User, RepoGroup, UserGroup
from kallithea.model.meta import Session
from kallithea.model.repo import RepoModel
from kallithea.model.user import UserModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.user_group import UserGroupModel
from kallithea.model.gist import GistModel

dn = os.path.dirname
FIXTURES = os.path.join(dn(dn(os.path.abspath(__file__))), 'tests', 'fixtures')


def error_function(*args, **kwargs):
    raise Exception('Total Crash !')


class Fixture(object):

    def __init__(self):
        pass

    def anon_access(self, status):
        """
        Context process for disabling anonymous access. use like:
        fixture = Fixture()
        with fixture.anon_access(False):
            #tests

        after this block anon access will be set to `not status`
        """

        class context(object):
            def __enter__(self):
                anon = User.get_default_user()
                anon.active = status
                Session().add(anon)
                Session().commit()
                time.sleep(1.5)  # must sleep for cache (1s to expire)

            def __exit__(self, exc_type, exc_val, exc_tb):
                anon = User.get_default_user()
                anon.active = not status
                Session().add(anon)
                Session().commit()

        return context()

    def _get_repo_create_params(self, **custom):
        defs = dict(
            repo_name=None,
            repo_type='hg',
            clone_uri='',
            repo_group='-1',
            repo_description='DESC',
            repo_private=False,
            repo_landing_rev='rev:tip',
            repo_copy_permissions=False,
            repo_state=Repository.STATE_CREATED,
        )
        defs.update(custom)
        if 'repo_name_full' not in custom:
            defs.update({'repo_name_full': defs['repo_name']})

        # fix the repo name if passed as repo_name_full
        if defs['repo_name']:
            defs['repo_name'] = defs['repo_name'].split('/')[-1]

        return defs

    def _get_group_create_params(self, **custom):
        defs = dict(
            group_name=None,
            group_description='DESC',
            group_parent_id=None,
            perms_updates=[],
            perms_new=[],
            enable_locking=False,
            recursive=False
        )
        defs.update(custom)

        return defs

    def _get_user_create_params(self, name, **custom):
        defs = dict(
            username=name,
            password='qweqwe',
            email='%s+test@example.com' % name,
            firstname='TestUser',
            lastname='Test',
            active=True,
            admin=False,
            extern_type='internal',
            extern_name=None
        )
        defs.update(custom)

        return defs

    def _get_user_group_create_params(self, name, **custom):
        defs = dict(
            users_group_name=name,
            user_group_description='DESC',
            users_group_active=True,
            user_group_data={},
        )
        defs.update(custom)

        return defs

    def create_repo(self, name, **kwargs):
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            r = Repository.get_by_repo_name(name)
            if r:
                return r

        if isinstance(kwargs.get('repo_group'), RepoGroup):
            kwargs['repo_group'] = kwargs['repo_group'].group_id

        form_data = self._get_repo_create_params(repo_name=name, **kwargs)
        cur_user = kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN)
        RepoModel().create(form_data, cur_user)
        Session().commit()
        return Repository.get_by_repo_name(name)

    def create_fork(self, repo_to_fork, fork_name, **kwargs):
        repo_to_fork = Repository.get_by_repo_name(repo_to_fork)

        form_data = self._get_repo_create_params(repo_name=fork_name,
                                            fork_parent_id=repo_to_fork,
                                            repo_type=repo_to_fork.repo_type,
                                            **kwargs)
        form_data['update_after_clone'] = False

        #TODO: fix it !!
        form_data['description'] = form_data['repo_description']
        form_data['private'] = form_data['repo_private']
        form_data['landing_rev'] = form_data['repo_landing_rev']

        owner = kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN)
        RepoModel().create_fork(form_data, cur_user=owner)
        Session().commit()
        r = Repository.get_by_repo_name(fork_name)
        assert r
        return r

    def destroy_repo(self, repo_name, **kwargs):
        RepoModel().delete(repo_name, **kwargs)
        Session().commit()

    def create_repo_group(self, name, **kwargs):
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            gr = RepoGroup.get_by_group_name(group_name=name)
            if gr:
                return gr
        form_data = self._get_group_create_params(group_name=name, **kwargs)
        owner = kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN)
        gr = RepoGroupModel().create(
            group_name=form_data['group_name'],
            group_description=form_data['group_name'],
            owner=owner, parent=form_data['group_parent_id'])
        Session().commit()
        gr = RepoGroup.get_by_group_name(gr.group_name)
        return gr

    def destroy_repo_group(self, repogroupid):
        RepoGroupModel().delete(repogroupid)
        Session().commit()

    def create_user(self, name, **kwargs):
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            user = User.get_by_username(name)
            if user:
                return user
        form_data = self._get_user_create_params(name, **kwargs)
        user = UserModel().create(form_data)
        Session().commit()
        user = User.get_by_username(user.username)
        return user

    def destroy_user(self, userid):
        UserModel().delete(userid)
        Session().commit()

    def create_user_group(self, name, **kwargs):
        if 'skip_if_exists' in kwargs:
            del kwargs['skip_if_exists']
            gr = UserGroup.get_by_group_name(group_name=name)
            if gr:
                return gr
        form_data = self._get_user_group_create_params(name, **kwargs)
        owner = kwargs.get('cur_user', TEST_USER_ADMIN_LOGIN)
        user_group = UserGroupModel().create(
            name=form_data['users_group_name'],
            description=form_data['user_group_description'],
            owner=owner, active=form_data['users_group_active'],
            group_data=form_data['user_group_data'])
        Session().commit()
        user_group = UserGroup.get_by_group_name(user_group.users_group_name)
        return user_group

    def destroy_user_group(self, usergroupid):
        UserGroupModel().delete(user_group=usergroupid, force=True)
        Session().commit()

    def create_gist(self, **kwargs):
        form_data = {
            'description': 'new-gist',
            'owner': TEST_USER_ADMIN_LOGIN,
            'gist_type': GistModel.cls.GIST_PUBLIC,
            'lifetime': -1,
            'gist_mapping': {'filename1.txt':{'content':'hello world'},}
        }
        form_data.update(kwargs)
        gist = GistModel().create(
            description=form_data['description'],owner=form_data['owner'],
            gist_mapping=form_data['gist_mapping'], gist_type=form_data['gist_type'],
            lifetime=form_data['lifetime']
        )
        Session().commit()

        return gist

    def destroy_gists(self, gistid=None):
        for g in GistModel.cls.get_all():
            if gistid:
                if gistid == g.gist_access_id:
                    GistModel().delete(g)
            else:
                GistModel().delete(g)
        Session().commit()

    def load_resource(self, resource_name, strip=True):
        with open(os.path.join(FIXTURES, resource_name)) as f:
            source = f.read()
            if strip:
                source = source.strip()

        return source
