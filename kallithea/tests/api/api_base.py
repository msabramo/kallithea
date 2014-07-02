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
tests for api. run with::

    KALLITHEA_WHOOSH_TEST_DISABLE=1 nosetests --with-coverage --cover-package=kallithea.controllers.api.api -x kallithea/tests/api
"""

from __future__ import with_statement
import os
import random
import mock

from kallithea.tests import *
from kallithea.tests.fixture import Fixture
from kallithea.lib.compat import json
from kallithea.lib.auth import AuthUser
from kallithea.model.user import UserModel
from kallithea.model.user_group import UserGroupModel
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.meta import Session
from kallithea.model.scm import ScmModel
from kallithea.model.gist import GistModel
from kallithea.model.db import Repository, User, Setting
from kallithea.lib.utils2 import time_to_datetime


API_URL = '/_admin/api'
TEST_USER_GROUP = 'test_user_group'
TEST_REPO_GROUP = 'test_repo_group'

fixture = Fixture()


def _build_data(apikey, method, **kw):
    """
    Builds API data with given random ID

    :param random_id:
    """
    random_id = random.randrange(1, 9999)
    return random_id, json.dumps({
        "id": random_id,
        "api_key": apikey,
        "method": method,
        "args": kw
    })


jsonify = lambda obj: json.loads(json.dumps(obj))


def crash(*args, **kwargs):
    raise Exception('Total Crash !')


def api_call(test_obj, params):
    response = test_obj.app.post(API_URL, content_type='application/json',
                                 params=params)
    return response


## helpers
def make_user_group(name=TEST_USER_GROUP):
    gr = fixture.create_user_group(name, cur_user=TEST_USER_ADMIN_LOGIN)
    UserGroupModel().add_user_to_group(user_group=gr,
                                       user=TEST_USER_ADMIN_LOGIN)
    Session().commit()
    return gr


def make_repo_group(name=TEST_REPO_GROUP):
    gr = fixture.create_repo_group(name, cur_user=TEST_USER_ADMIN_LOGIN)
    Session().commit()
    return gr


class BaseTestApi(object):
    REPO = None
    REPO_TYPE = None

    @classmethod
    def setup_class(cls):
        cls.usr = UserModel().get_by_username(TEST_USER_ADMIN_LOGIN)
        cls.apikey = cls.usr.api_key
        cls.test_user = UserModel().create_or_update(
            username='test-api',
            password='test',
            email='test@example.com',
            firstname='first',
            lastname='last'
        )
        Session().commit()
        cls.TEST_USER_LOGIN = cls.test_user.username
        cls.apikey_regular = cls.test_user.api_key

    @classmethod
    def teardown_class(cls):
        pass

    def setUp(self):
        self.maxDiff = None
        make_user_group()
        make_repo_group()

    def tearDown(self):
        fixture.destroy_user_group(TEST_USER_GROUP)
        fixture.destroy_gists()
        fixture.destroy_repo_group(TEST_REPO_GROUP)

    def _compare_ok(self, id_, expected, given):
        expected = jsonify({
            'id': id_,
            'error': None,
            'result': expected
        })
        given = json.loads(given)
        self.assertEqual(expected, given)

    def _compare_error(self, id_, expected, given):
        expected = jsonify({
            'id': id_,
            'error': expected,
            'result': None
        })
        given = json.loads(given)
        self.assertEqual(expected, given)

    def test_Optional_object(self):
        from kallithea.controllers.api.api import Optional

        option1 = Optional(None)
        self.assertEqual('<Optional:%s>' % None, repr(option1))
        self.assertEqual(option1(), None)

        self.assertEqual(1, Optional.extract(Optional(1)))
        self.assertEqual('trololo', Optional.extract('trololo'))

    def test_Optional_OAttr(self):
        from kallithea.controllers.api.api import Optional, OAttr

        option1 = Optional(OAttr('apiuser'))
        self.assertEqual('apiuser', Optional.extract(option1))

    def test_OAttr_object(self):
        from kallithea.controllers.api.api import OAttr

        oattr1 = OAttr('apiuser')
        self.assertEqual('<OptionalAttr:apiuser>', repr(oattr1))
        self.assertEqual(oattr1(), oattr1)

    def test_api_wrong_key(self):
        id_, params = _build_data('trololo', 'get_user')
        response = api_call(self, params)

        expected = 'Invalid API KEY'
        self._compare_error(id_, expected, given=response.body)

    def test_api_missing_non_optional_param(self):
        id_, params = _build_data(self.apikey, 'get_repo')
        response = api_call(self, params)

        expected = 'Missing non optional `repoid` arg in JSON DATA'
        self._compare_error(id_, expected, given=response.body)

    def test_api_missing_non_optional_param_args_null(self):
        id_, params = _build_data(self.apikey, 'get_repo')
        params = params.replace('"args": {}', '"args": null')
        response = api_call(self, params)

        expected = 'Missing non optional `repoid` arg in JSON DATA'
        self._compare_error(id_, expected, given=response.body)

    def test_api_missing_non_optional_param_args_bad(self):
        id_, params = _build_data(self.apikey, 'get_repo')
        params = params.replace('"args": {}', '"args": 1')
        response = api_call(self, params)

        expected = 'Missing non optional `repoid` arg in JSON DATA'
        self._compare_error(id_, expected, given=response.body)

    def test_api_args_is_null(self):
        id_, params = _build_data(self.apikey, 'get_users', )
        params = params.replace('"args": {}', '"args": null')
        response = api_call(self, params)
        self.assertEqual(response.status, '200 OK')

    def test_api_args_is_bad(self):
        id_, params = _build_data(self.apikey, 'get_users', )
        params = params.replace('"args": {}', '"args": 1')
        response = api_call(self, params)
        self.assertEqual(response.status, '200 OK')

    def test_api_args_different_args(self):
        import string
        expected = {
            'ascii_letters': string.ascii_letters,
            'ws': string.whitespace,
            'printables': string.printable
        }
        id_, params = _build_data(self.apikey, 'test', args=expected)
        response = api_call(self, params)
        self.assertEqual(response.status, '200 OK')
        self._compare_ok(id_, expected, response.body)

    def test_api_get_users(self):
        id_, params = _build_data(self.apikey, 'get_users', )
        response = api_call(self, params)
        ret_all = []
        _users = User.query().filter(User.username != User.DEFAULT_USER) \
            .order_by(User.username).all()
        for usr in _users:
            ret = usr.get_api_data()
            ret_all.append(jsonify(ret))
        expected = ret_all
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_user(self):
        id_, params = _build_data(self.apikey, 'get_user',
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)

        usr = UserModel().get_by_username(TEST_USER_ADMIN_LOGIN)
        ret = usr.get_api_data()
        ret['permissions'] = AuthUser(usr.user_id).permissions

        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_user_that_does_not_exist(self):
        id_, params = _build_data(self.apikey, 'get_user',
                                  userid='trololo')
        response = api_call(self, params)

        expected = "user `%s` does not exist" % 'trololo'
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_user_without_giving_userid(self):
        id_, params = _build_data(self.apikey, 'get_user')
        response = api_call(self, params)

        usr = UserModel().get_by_username(TEST_USER_ADMIN_LOGIN)
        ret = usr.get_api_data()
        ret['permissions'] = AuthUser(usr.user_id).permissions

        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_user_without_giving_userid_non_admin(self):
        id_, params = _build_data(self.apikey_regular, 'get_user')
        response = api_call(self, params)

        usr = UserModel().get_by_username(self.TEST_USER_LOGIN)
        ret = usr.get_api_data()
        ret['permissions'] = AuthUser(usr.user_id).permissions

        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_user_with_giving_userid_non_admin(self):
        id_, params = _build_data(self.apikey_regular, 'get_user',
                                  userid=self.TEST_USER_LOGIN)
        response = api_call(self, params)

        expected = 'userid is not the same as your user'
        self._compare_error(id_, expected, given=response.body)

    def test_api_pull(self):
        repo_name = 'test_pull'
        r = fixture.create_repo(repo_name, repo_type=self.REPO_TYPE)
        r.clone_uri = os.path.join(TESTS_TMP_PATH, self.REPO)
        Session.add(r)
        Session.commit()

        id_, params = _build_data(self.apikey, 'pull',
                                  repoid=repo_name,)
        response = api_call(self, params)

        expected = {'msg': 'Pulled from `%s`' % repo_name,
                    'repository': repo_name}
        self._compare_ok(id_, expected, given=response.body)

        fixture.destroy_repo(repo_name)

    def test_api_pull_error(self):
        id_, params = _build_data(self.apikey, 'pull',
                                  repoid=self.REPO, )
        response = api_call(self, params)

        expected = 'Unable to pull changes from `%s`' % self.REPO
        self._compare_error(id_, expected, given=response.body)

    def test_api_rescan_repos(self):
        id_, params = _build_data(self.apikey, 'rescan_repos')
        response = api_call(self, params)

        expected = {'added': [], 'removed': []}
        self._compare_ok(id_, expected, given=response.body)

    @mock.patch.object(ScmModel, 'repo_scan', crash)
    def test_api_rescann_error(self):
        id_, params = _build_data(self.apikey, 'rescan_repos', )
        response = api_call(self, params)

        expected = 'Error occurred during rescan repositories action'
        self._compare_error(id_, expected, given=response.body)

    def test_api_invalidate_cache(self):
        repo = RepoModel().get_by_repo_name(self.REPO)
        repo.scm_instance_cached()  # seed cache

        id_, params = _build_data(self.apikey, 'invalidate_cache',
                                  repoid=self.REPO)
        response = api_call(self, params)

        expected = {
            'msg': "Cache for repository `%s` was invalidated" % (self.REPO,),
            'repository': self.REPO
        }
        self._compare_ok(id_, expected, given=response.body)

    @mock.patch.object(ScmModel, 'mark_for_invalidation', crash)
    def test_api_invalidate_cache_error(self):
        id_, params = _build_data(self.apikey, 'invalidate_cache',
                                  repoid=self.REPO)
        response = api_call(self, params)

        expected = 'Error occurred during cache invalidation action'
        self._compare_error(id_, expected, given=response.body)

    def test_api_invalidate_cache_regular_user_no_permission(self):
        repo = RepoModel().get_by_repo_name(self.REPO)
        repo.scm_instance_cached() # seed cache

        id_, params = _build_data(self.apikey_regular, 'invalidate_cache',
                                  repoid=self.REPO)
        response = api_call(self, params)

        expected = "repository `%s` does not exist" % (self.REPO,)
        self._compare_error(id_, expected, given=response.body)

    def test_api_lock_repo_lock_aquire(self):
        id_, params = _build_data(self.apikey, 'lock',
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  repoid=self.REPO,
                                  locked=True)
        response = api_call(self, params)
        expected = {
            'repo': self.REPO, 'locked': True,
            'locked_since': response.json['result']['locked_since'],
            'locked_by': TEST_USER_ADMIN_LOGIN,
            'lock_state_changed': True,
            'msg': ('User `%s` set lock state for repo `%s` to `%s`'
                    % (TEST_USER_ADMIN_LOGIN, self.REPO, True))
        }
        self._compare_ok(id_, expected, given=response.body)

    def test_api_lock_repo_lock_aquire_by_non_admin(self):
        repo_name = 'api_delete_me'
        fixture.create_repo(repo_name, repo_type=self.REPO_TYPE,
                            cur_user=self.TEST_USER_LOGIN)
        try:
            id_, params = _build_data(self.apikey_regular, 'lock',
                                      repoid=repo_name,
                                      locked=True)
            response = api_call(self, params)
            expected = {
                'repo': repo_name,
                'locked': True,
                'locked_since': response.json['result']['locked_since'],
                'locked_by': self.TEST_USER_LOGIN,
                'lock_state_changed': True,
                'msg': ('User `%s` set lock state for repo `%s` to `%s`'
                        % (self.TEST_USER_LOGIN, repo_name, True))
            }
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_lock_repo_lock_aquire_non_admin_with_userid(self):
        repo_name = 'api_delete_me'
        fixture.create_repo(repo_name, repo_type=self.REPO_TYPE,
                            cur_user=self.TEST_USER_LOGIN)
        try:
            id_, params = _build_data(self.apikey_regular, 'lock',
                                      userid=TEST_USER_ADMIN_LOGIN,
                                      repoid=repo_name,
                                      locked=True)
            response = api_call(self, params)
            expected = 'userid is not the same as your user'
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_lock_repo_lock_aquire_non_admin_not_his_repo(self):
        id_, params = _build_data(self.apikey_regular, 'lock',
                                  repoid=self.REPO,
                                  locked=True)
        response = api_call(self, params)
        expected = 'repository `%s` does not exist' % (self.REPO)
        self._compare_error(id_, expected, given=response.body)

    def test_api_lock_repo_lock_release(self):
        id_, params = _build_data(self.apikey, 'lock',
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  repoid=self.REPO,
                                  locked=False)
        response = api_call(self, params)
        expected = {
            'repo': self.REPO,
            'locked': False,
            'locked_since': None,
            'locked_by': TEST_USER_ADMIN_LOGIN,
            'lock_state_changed': True,
            'msg': ('User `%s` set lock state for repo `%s` to `%s`'
                    % (TEST_USER_ADMIN_LOGIN, self.REPO, False))
        }
        self._compare_ok(id_, expected, given=response.body)

    def test_api_lock_repo_lock_aquire_optional_userid(self):
        id_, params = _build_data(self.apikey, 'lock',
                                  repoid=self.REPO,
                                  locked=True)
        response = api_call(self, params)
        time_ = response.json['result']['locked_since']
        expected = {
            'repo': self.REPO,
            'locked': True,
            'locked_since': time_,
            'locked_by': TEST_USER_ADMIN_LOGIN,
            'lock_state_changed': True,
            'msg': ('User `%s` set lock state for repo `%s` to `%s`'
                    % (TEST_USER_ADMIN_LOGIN, self.REPO, True))
        }

        self._compare_ok(id_, expected, given=response.body)

    def test_api_lock_repo_lock_optional_locked(self):
        id_, params = _build_data(self.apikey, 'lock',
                                  repoid=self.REPO)
        response = api_call(self, params)
        time_ = response.json['result']['locked_since']
        expected = {
            'repo': self.REPO,
            'locked': True,
            'locked_since': time_,
            'locked_by': TEST_USER_ADMIN_LOGIN,
            'lock_state_changed': False,
            'msg': ('Repo `%s` locked by `%s` on `%s`.'
                    % (self.REPO, TEST_USER_ADMIN_LOGIN,
                       json.dumps(time_to_datetime(time_))))
        }
        self._compare_ok(id_, expected, given=response.body)

    def test_api_lock_repo_lock_optional_not_locked(self):
        repo_name = 'api_not_locked'
        repo = fixture.create_repo(repo_name, repo_type=self.REPO_TYPE,
                            cur_user=self.TEST_USER_LOGIN)
        self.assertEqual(repo.locked, [None, None])
        try:
            id_, params = _build_data(self.apikey, 'lock',
                                      repoid=repo.repo_id)
            response = api_call(self, params)
            expected = {
                'repo': repo_name,
                'locked': False,
                'locked_since': None,
                'locked_by': None,
                'lock_state_changed': False,
                'msg': ('Repo `%s` not locked.' % (repo_name,))
            }
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    @mock.patch.object(Repository, 'lock', crash)
    def test_api_lock_error(self):
        id_, params = _build_data(self.apikey, 'lock',
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  repoid=self.REPO,
                                  locked=True)
        response = api_call(self, params)

        expected = 'Error occurred locking repository `%s`' % self.REPO
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_locks_regular_user(self):
        id_, params = _build_data(self.apikey_regular, 'get_locks')
        response = api_call(self, params)
        expected = []
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_locks_with_userid_regular_user(self):
        id_, params = _build_data(self.apikey_regular, 'get_locks',
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)
        expected = 'userid is not the same as your user'
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_locks(self):
        id_, params = _build_data(self.apikey, 'get_locks')
        response = api_call(self, params)
        expected = []
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_locks_with_one_locked_repo(self):
        repo_name = 'api_delete_me'
        repo = fixture.create_repo(repo_name, repo_type=self.REPO_TYPE,
                                   cur_user=self.TEST_USER_LOGIN)
        Repository.lock(repo, User.get_by_username(self.TEST_USER_LOGIN).user_id)
        try:
            id_, params = _build_data(self.apikey, 'get_locks')
            response = api_call(self, params)
            expected = [repo.get_api_data()]
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_get_locks_with_one_locked_repo_for_specific_user(self):
        repo_name = 'api_delete_me'
        repo = fixture.create_repo(repo_name, repo_type=self.REPO_TYPE,
                                   cur_user=self.TEST_USER_LOGIN)
        Repository.lock(repo, User.get_by_username(self.TEST_USER_LOGIN).user_id)
        try:
            id_, params = _build_data(self.apikey, 'get_locks',
                                      userid=self.TEST_USER_LOGIN)
            response = api_call(self, params)
            expected = [repo.get_api_data()]
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_get_locks_with_userid(self):
        id_, params = _build_data(self.apikey, 'get_locks',
                                  userid=TEST_USER_REGULAR_LOGIN)
        response = api_call(self, params)
        expected = []
        self._compare_ok(id_, expected, given=response.body)

    def test_api_create_existing_user(self):
        id_, params = _build_data(self.apikey, 'create_user',
                                  username=TEST_USER_ADMIN_LOGIN,
                                  email='test@foo.com',
                                  password='trololo')
        response = api_call(self, params)

        expected = "user `%s` already exist" % TEST_USER_ADMIN_LOGIN
        self._compare_error(id_, expected, given=response.body)

    def test_api_create_user_with_existing_email(self):
        id_, params = _build_data(self.apikey, 'create_user',
                                  username=TEST_USER_ADMIN_LOGIN + 'new',
                                  email=TEST_USER_REGULAR_EMAIL,
                                  password='trololo')
        response = api_call(self, params)

        expected = "email `%s` already exist" % TEST_USER_REGULAR_EMAIL
        self._compare_error(id_, expected, given=response.body)

    def test_api_create_user(self):
        username = 'test_new_api_user'
        email = username + "@foo.com"

        id_, params = _build_data(self.apikey, 'create_user',
                                  username=username,
                                  email=email,
                                  password='trololo')
        response = api_call(self, params)

        usr = UserModel().get_by_username(username)
        ret = dict(
            msg='created new user `%s`' % username,
            user=jsonify(usr.get_api_data())
        )

        try:
            expected = ret
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_user(usr.user_id)

    def test_api_create_user_without_password(self):
        username = 'test_new_api_user_passwordless'
        email = username + "@foo.com"

        id_, params = _build_data(self.apikey, 'create_user',
                                  username=username,
                                  email=email)
        response = api_call(self, params)

        usr = UserModel().get_by_username(username)
        ret = dict(
            msg='created new user `%s`' % username,
            user=jsonify(usr.get_api_data())
        )
        try:
            expected = ret
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_user(usr.user_id)

    def test_api_create_user_with_extern_name(self):
        username = 'test_new_api_user_passwordless'
        email = username + "@foo.com"

        id_, params = _build_data(self.apikey, 'create_user',
                                  username=username,
                                  email=email, extern_name='internal')
        response = api_call(self, params)

        usr = UserModel().get_by_username(username)
        ret = dict(
            msg='created new user `%s`' % username,
            user=jsonify(usr.get_api_data())
        )
        try:
            expected = ret
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_user(usr.user_id)

    @mock.patch.object(UserModel, 'create_or_update', crash)
    def test_api_create_user_when_exception_happened(self):

        username = 'test_new_api_user'
        email = username + "@foo.com"

        id_, params = _build_data(self.apikey, 'create_user',
                                  username=username,
                                  email=email,
                                  password='trololo')
        response = api_call(self, params)
        expected = 'failed to create user `%s`' % username
        self._compare_error(id_, expected, given=response.body)

    def test_api_delete_user(self):
        usr = UserModel().create_or_update(username=u'test_user',
                                           password=u'qweqwe',
                                           email=u'u232@example.com',
                                           firstname=u'u1', lastname=u'u1')
        Session().commit()
        username = usr.username
        email = usr.email
        usr_id = usr.user_id
        ## DELETE THIS USER NOW

        id_, params = _build_data(self.apikey, 'delete_user',
                                  userid=username, )
        response = api_call(self, params)

        ret = {'msg': 'deleted user ID:%s %s' % (usr_id, username),
               'user': None}
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    @mock.patch.object(UserModel, 'delete', crash)
    def test_api_delete_user_when_exception_happened(self):
        usr = UserModel().create_or_update(username=u'test_user',
                                           password=u'qweqwe',
                                           email=u'u232@example.com',
                                           firstname=u'u1', lastname=u'u1')
        Session().commit()
        username = usr.username

        id_, params = _build_data(self.apikey, 'delete_user',
                                  userid=username, )
        response = api_call(self, params)
        ret = 'failed to delete user ID:%s %s' % (usr.user_id,
                                                  usr.username)
        expected = ret
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([('firstname', 'new_username'),
                           ('lastname', 'new_username'),
                           ('email', 'new_username'),
                           ('admin', True),
                           ('admin', False),
                           ('extern_type', 'ldap'),
                           ('extern_type', None),
                           ('extern_name', 'test'),
                           ('extern_name', None),
                           ('active', False),
                           ('active', True),
                           ('password', 'newpass')
    ])
    def test_api_update_user(self, name, expected):
        usr = UserModel().get_by_username(self.TEST_USER_LOGIN)
        kw = {name: expected,
              'userid': usr.user_id}
        id_, params = _build_data(self.apikey, 'update_user', **kw)
        response = api_call(self, params)

        ret = {
            'msg': 'updated user ID:%s %s' % (
                usr.user_id, self.TEST_USER_LOGIN),
            'user': jsonify(UserModel() \
                .get_by_username(self.TEST_USER_LOGIN) \
                .get_api_data())
        }

        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_update_user_no_changed_params(self):
        usr = UserModel().get_by_username(TEST_USER_ADMIN_LOGIN)
        ret = jsonify(usr.get_api_data())
        id_, params = _build_data(self.apikey, 'update_user',
                                  userid=TEST_USER_ADMIN_LOGIN)

        response = api_call(self, params)
        ret = {
            'msg': 'updated user ID:%s %s' % (
                usr.user_id, TEST_USER_ADMIN_LOGIN),
            'user': ret
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_update_user_by_user_id(self):
        usr = UserModel().get_by_username(TEST_USER_ADMIN_LOGIN)
        ret = jsonify(usr.get_api_data())
        id_, params = _build_data(self.apikey, 'update_user',
                                  userid=usr.user_id)

        response = api_call(self, params)
        ret = {
            'msg': 'updated user ID:%s %s' % (
                usr.user_id, TEST_USER_ADMIN_LOGIN),
            'user': ret
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_update_user_default_user(self):
        usr = User.get_default_user()
        id_, params = _build_data(self.apikey, 'update_user',
                                  userid=usr.user_id)

        response = api_call(self, params)
        expected = 'editing default user is forbidden'
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(UserModel, 'update_user', crash)
    def test_api_update_user_when_exception_happens(self):
        usr = UserModel().get_by_username(TEST_USER_ADMIN_LOGIN)
        ret = jsonify(usr.get_api_data())
        id_, params = _build_data(self.apikey, 'update_user',
                                  userid=usr.user_id)

        response = api_call(self, params)
        ret = 'failed to update user `%s`' % usr.user_id

        expected = ret
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_repo(self):
        new_group = 'some_new_group'
        make_user_group(new_group)
        RepoModel().grant_user_group_permission(repo=self.REPO,
                                                group_name=new_group,
                                                perm='repository.read')
        Session().commit()
        id_, params = _build_data(self.apikey, 'get_repo',
                                  repoid=self.REPO)
        response = api_call(self, params)

        repo = RepoModel().get_by_repo_name(self.REPO)
        ret = repo.get_api_data()

        members = []
        followers = []
        for user in repo.repo_to_perm:
            perm = user.permission.permission_name
            user = user.user
            user_data = {'name': user.username, 'type': "user",
                         'permission': perm}
            members.append(user_data)

        for user_group in repo.users_group_to_perm:
            perm = user_group.permission.permission_name
            user_group = user_group.users_group
            user_group_data = {'name': user_group.users_group_name,
                               'type': "user_group", 'permission': perm}
            members.append(user_group_data)

        for user in repo.followers:
            followers.append(user.user.get_api_data())

        ret['members'] = members
        ret['followers'] = followers

        expected = ret
        self._compare_ok(id_, expected, given=response.body)
        fixture.destroy_user_group(new_group)

    @parameterized.expand([
        ('repository.admin',),
        ('repository.write',),
        ('repository.read',),
    ])
    def test_api_get_repo_by_non_admin(self, grant_perm):
        RepoModel().grant_user_permission(repo=self.REPO,
                                          user=self.TEST_USER_LOGIN,
                                          perm=grant_perm)
        Session().commit()
        id_, params = _build_data(self.apikey_regular, 'get_repo',
                                  repoid=self.REPO)
        response = api_call(self, params)

        repo = RepoModel().get_by_repo_name(self.REPO)
        ret = repo.get_api_data()

        members = []
        followers = []
        self.assertEqual(2, len(repo.repo_to_perm))
        for user in repo.repo_to_perm:
            perm = user.permission.permission_name
            user_obj = user.user
            user_data = {'name': user_obj.username, 'type': "user",
                         'permission': perm}
            members.append(user_data)

        for user_group in repo.users_group_to_perm:
            perm = user_group.permission.permission_name
            user_group_obj = user_group.users_group
            user_group_data = {'name': user_group_obj.users_group_name,
                               'type': "user_group", 'permission': perm}
            members.append(user_group_data)

        for user in repo.followers:
            followers.append(user.user.get_api_data())

        ret['members'] = members
        ret['followers'] = followers

        expected = ret
        try:
            self._compare_ok(id_, expected, given=response.body)
        finally:
            RepoModel().revoke_user_permission(self.REPO, self.TEST_USER_LOGIN)

    def test_api_get_repo_by_non_admin_no_permission_to_repo(self):
        RepoModel().grant_user_permission(repo=self.REPO,
                                          user=self.TEST_USER_LOGIN,
                                          perm='repository.none')

        id_, params = _build_data(self.apikey_regular, 'get_repo',
                                  repoid=self.REPO)
        response = api_call(self, params)

        expected = 'repository `%s` does not exist' % (self.REPO)
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_repo_that_doesn_not_exist(self):
        id_, params = _build_data(self.apikey, 'get_repo',
                                  repoid='no-such-repo')
        response = api_call(self, params)

        ret = 'repository `%s` does not exist' % 'no-such-repo'
        expected = ret
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_repos(self):
        id_, params = _build_data(self.apikey, 'get_repos')
        response = api_call(self, params)

        result = []
        for repo in RepoModel().get_all():
            result.append(repo.get_api_data())
        ret = jsonify(result)

        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_repos_non_admin(self):
        id_, params = _build_data(self.apikey_regular, 'get_repos')
        response = api_call(self, params)

        result = []
        for repo in RepoModel().get_all_user_repos(self.TEST_USER_LOGIN):
            result.append(repo.get_api_data())
        ret = jsonify(result)

        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    @parameterized.expand([('all', 'all'),
                           ('dirs', 'dirs'),
                           ('files', 'files'), ])
    def test_api_get_repo_nodes(self, name, ret_type):
        rev = 'tip'
        path = '/'
        id_, params = _build_data(self.apikey, 'get_repo_nodes',
                                  repoid=self.REPO, revision=rev,
                                  root_path=path,
                                  ret_type=ret_type)
        response = api_call(self, params)

        # we don't the actual return types here since it's tested somewhere
        # else
        expected = response.json['result']
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_repo_nodes_bad_revisions(self):
        rev = 'i-dont-exist'
        path = '/'
        id_, params = _build_data(self.apikey, 'get_repo_nodes',
                                  repoid=self.REPO, revision=rev,
                                  root_path=path, )
        response = api_call(self, params)

        expected = 'failed to get repo: `%s` nodes' % self.REPO
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_repo_nodes_bad_path(self):
        rev = 'tip'
        path = '/idontexits'
        id_, params = _build_data(self.apikey, 'get_repo_nodes',
                                  repoid=self.REPO, revision=rev,
                                  root_path=path, )
        response = api_call(self, params)

        expected = 'failed to get repo: `%s` nodes' % self.REPO
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_repo_nodes_bad_ret_type(self):
        rev = 'tip'
        path = '/'
        ret_type = 'error'
        id_, params = _build_data(self.apikey, 'get_repo_nodes',
                                  repoid=self.REPO, revision=rev,
                                  root_path=path,
                                  ret_type=ret_type)
        response = api_call(self, params)

        expected = ('ret_type must be one of %s'
                    % (','.join(['files', 'dirs', 'all'])))
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([('all', 'all', 'repository.write'),
                           ('dirs', 'dirs', 'repository.admin'),
                           ('files', 'files', 'repository.read'), ])
    def test_api_get_repo_nodes_by_regular_user(self, name, ret_type, grant_perm):
        RepoModel().grant_user_permission(repo=self.REPO,
                                          user=self.TEST_USER_LOGIN,
                                          perm=grant_perm)
        Session().commit()

        rev = 'tip'
        path = '/'
        id_, params = _build_data(self.apikey_regular, 'get_repo_nodes',
                                  repoid=self.REPO, revision=rev,
                                  root_path=path,
                                  ret_type=ret_type)
        response = api_call(self, params)

        # we don't the actual return types here since it's tested somewhere
        # else
        expected = response.json['result']
        try:
            self._compare_ok(id_, expected, given=response.body)
        finally:
            RepoModel().revoke_user_permission(self.REPO, self.TEST_USER_LOGIN)

    def test_api_create_repo(self):
        repo_name = 'api-repo'
        id_, params = _build_data(self.apikey, 'create_repo',
                                  repo_name=repo_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
                                  repo_type=self.REPO_TYPE,
        )
        response = api_call(self, params)

        repo = RepoModel().get_by_repo_name(repo_name)
        self.assertNotEqual(repo, None)
        ret = {
            'msg': 'Created new repository `%s`' % repo_name,
            'success': True,
            'task': None,
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)
        fixture.destroy_repo(repo_name)

    def test_api_create_repo_in_group(self):
        repo_name = 'my_gr/api-repo'
        id_, params = _build_data(self.apikey, 'create_repo',
                                  repo_name=repo_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
                                  repo_type=self.REPO_TYPE,)
        response = api_call(self, params)
        print params
        repo = RepoModel().get_by_repo_name(repo_name)
        self.assertNotEqual(repo, None)
        ret = {
            'msg': 'Created new repository `%s`' % repo_name,
            'success': True,
            'task': None,
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)
        fixture.destroy_repo(repo_name)
        fixture.destroy_repo_group('my_gr')

    def test_api_create_repo_unknown_owner(self):
        repo_name = 'api-repo'
        owner = 'i-dont-exist'
        id_, params = _build_data(self.apikey, 'create_repo',
                                  repo_name=repo_name,
                                  owner=owner,
                                  repo_type=self.REPO_TYPE,
        )
        response = api_call(self, params)
        expected = 'user `%s` does not exist' % owner
        self._compare_error(id_, expected, given=response.body)

    def test_api_create_repo_dont_specify_owner(self):
        repo_name = 'api-repo'
        owner = 'i-dont-exist'
        id_, params = _build_data(self.apikey, 'create_repo',
                                  repo_name=repo_name,
                                  repo_type=self.REPO_TYPE,
        )
        response = api_call(self, params)

        repo = RepoModel().get_by_repo_name(repo_name)
        self.assertNotEqual(repo, None)
        ret = {
            'msg': 'Created new repository `%s`' % repo_name,
            'success': True,
            'task': None,
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)
        fixture.destroy_repo(repo_name)

    def test_api_create_repo_by_non_admin(self):
        repo_name = 'api-repo'
        owner = 'i-dont-exist'
        id_, params = _build_data(self.apikey_regular, 'create_repo',
                                  repo_name=repo_name,
                                  repo_type=self.REPO_TYPE,
        )
        response = api_call(self, params)

        repo = RepoModel().get_by_repo_name(repo_name)
        self.assertNotEqual(repo, None)
        ret = {
            'msg': 'Created new repository `%s`' % repo_name,
            'success': True,
            'task': None,
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)
        fixture.destroy_repo(repo_name)

    def test_api_create_repo_by_non_admin_specify_owner(self):
        repo_name = 'api-repo'
        owner = 'i-dont-exist'
        id_, params = _build_data(self.apikey_regular, 'create_repo',
                                  repo_name=repo_name,
                                  repo_type=self.REPO_TYPE,
                                  owner=owner)
        response = api_call(self, params)

        expected = 'Only Kallithea admin can specify `owner` param'
        self._compare_error(id_, expected, given=response.body)
        fixture.destroy_repo(repo_name)

    def test_api_create_repo_exists(self):
        repo_name = self.REPO
        id_, params = _build_data(self.apikey, 'create_repo',
                                  repo_name=repo_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
                                  repo_type=self.REPO_TYPE,)
        response = api_call(self, params)
        expected = "repo `%s` already exist" % repo_name
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoModel, 'create', crash)
    def test_api_create_repo_exception_occurred(self):
        repo_name = 'api-repo'
        id_, params = _build_data(self.apikey, 'create_repo',
                                  repo_name=repo_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
                                  repo_type=self.REPO_TYPE,)
        response = api_call(self, params)
        expected = 'failed to create repository `%s`' % repo_name
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([
        ('owner', {'owner': TEST_USER_REGULAR_LOGIN}),
        ('description', {'description': 'new description'}),
        ('active', {'active': True}),
        ('active', {'active': False}),
        ('clone_uri', {'clone_uri': 'http://foo.com/repo'}),
        ('clone_uri', {'clone_uri': None}),
        ('landing_rev', {'landing_rev': 'branch:master'}),
        ('enable_statistics', {'enable_statistics': True}),
        ('enable_locking', {'enable_locking': True}),
        ('enable_downloads', {'enable_downloads': True}),
        ('name', {'name': 'new_repo_name'}),
        ('repo_group', {'group': 'test_group_for_update'}),
    ])
    def test_api_update_repo(self, changing_attr, updates):
        repo_name = 'api_update_me'
        repo = fixture.create_repo(repo_name, repo_type=self.REPO_TYPE)
        if changing_attr == 'repo_group':
            fixture.create_repo_group(updates['group'])

        id_, params = _build_data(self.apikey, 'update_repo',
                                  repoid=repo_name, **updates)
        response = api_call(self, params)
        if changing_attr == 'name':
            repo_name = updates['name']
        if changing_attr == 'repo_group':
            repo_name = '/'.join([updates['group'], repo_name])
        try:
            expected = {
                'msg': 'updated repo ID:%s %s' % (repo.repo_id, repo_name),
                'repository': repo.get_api_data()
            }
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)
            if changing_attr == 'repo_group':
                fixture.destroy_repo_group(updates['group'])

    def test_api_update_repo_repo_group_does_not_exist(self):
        repo_name = 'admin_owned'
        fixture.create_repo(repo_name)
        updates = {'group': 'test_group_for_update'}
        id_, params = _build_data(self.apikey, 'update_repo',
                                  repoid=repo_name, **updates)
        response = api_call(self, params)
        try:
            expected = 'repository group `%s` does not exist' % updates['group']
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_update_repo_regular_user_not_allowed(self):
        repo_name = 'admin_owned'
        fixture.create_repo(repo_name)
        updates = {'active': False}
        id_, params = _build_data(self.apikey_regular, 'update_repo',
                                  repoid=repo_name, **updates)
        response = api_call(self, params)
        try:
            expected = 'repository `%s` does not exist' % repo_name
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    @mock.patch.object(RepoModel, 'update', crash)
    def test_api_update_repo_exception_occured(self):
        repo_name = 'api_update_me'
        fixture.create_repo(repo_name, repo_type=self.REPO_TYPE)
        id_, params = _build_data(self.apikey, 'update_repo',
                                  repoid=repo_name, owner=TEST_USER_ADMIN_LOGIN,)
        response = api_call(self, params)
        try:
            expected = 'failed to update repo `%s`' % repo_name
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_delete_repo(self):
        repo_name = 'api_delete_me'
        fixture.create_repo(repo_name, repo_type=self.REPO_TYPE)

        id_, params = _build_data(self.apikey, 'delete_repo',
                                  repoid=repo_name, )
        response = api_call(self, params)

        ret = {
            'msg': 'Deleted repository `%s`' % repo_name,
            'success': True
        }
        try:
            expected = ret
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_delete_repo_by_non_admin(self):
        repo_name = 'api_delete_me'
        fixture.create_repo(repo_name, repo_type=self.REPO_TYPE,
                            cur_user=self.TEST_USER_LOGIN)
        id_, params = _build_data(self.apikey_regular, 'delete_repo',
                                  repoid=repo_name, )
        response = api_call(self, params)

        ret = {
            'msg': 'Deleted repository `%s`' % repo_name,
            'success': True
        }
        try:
            expected = ret
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_delete_repo_by_non_admin_no_permission(self):
        repo_name = 'api_delete_me'
        fixture.create_repo(repo_name, repo_type=self.REPO_TYPE)
        try:
            id_, params = _build_data(self.apikey_regular, 'delete_repo',
                                      repoid=repo_name, )
            response = api_call(self, params)
            expected = 'repository `%s` does not exist' % (repo_name)
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_delete_repo_exception_occurred(self):
        repo_name = 'api_delete_me'
        fixture.create_repo(repo_name, repo_type=self.REPO_TYPE)
        try:
            with mock.patch.object(RepoModel, 'delete', crash):
                id_, params = _build_data(self.apikey, 'delete_repo',
                                          repoid=repo_name, )
                response = api_call(self, params)

                expected = 'failed to delete repository `%s`' % repo_name
                self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(repo_name)

    def test_api_fork_repo(self):
        fork_name = 'api-repo-fork'
        id_, params = _build_data(self.apikey, 'fork_repo',
                                  repoid=self.REPO,
                                  fork_name=fork_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
        )
        response = api_call(self, params)

        ret = {
            'msg': 'Created fork of `%s` as `%s`' % (self.REPO,
                                                     fork_name),
            'success': True,
            'task': None,
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)
        fixture.destroy_repo(fork_name)

    def test_api_fork_repo_non_admin(self):
        fork_name = 'api-repo-fork'
        id_, params = _build_data(self.apikey_regular, 'fork_repo',
                                  repoid=self.REPO,
                                  fork_name=fork_name,
        )
        response = api_call(self, params)

        ret = {
            'msg': 'Created fork of `%s` as `%s`' % (self.REPO,
                                                     fork_name),
            'success': True,
            'task': None,
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)
        fixture.destroy_repo(fork_name)

    def test_api_fork_repo_non_admin_specify_owner(self):
        fork_name = 'api-repo-fork'
        id_, params = _build_data(self.apikey_regular, 'fork_repo',
                                  repoid=self.REPO,
                                  fork_name=fork_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
        )
        response = api_call(self, params)
        expected = 'Only Kallithea admin can specify `owner` param'
        self._compare_error(id_, expected, given=response.body)
        fixture.destroy_repo(fork_name)

    def test_api_fork_repo_non_admin_no_permission_to_fork(self):
        RepoModel().grant_user_permission(repo=self.REPO,
                                          user=self.TEST_USER_LOGIN,
                                          perm='repository.none')
        fork_name = 'api-repo-fork'
        id_, params = _build_data(self.apikey_regular, 'fork_repo',
                                  repoid=self.REPO,
                                  fork_name=fork_name,
        )
        response = api_call(self, params)
        expected = 'repository `%s` does not exist' % (self.REPO)
        self._compare_error(id_, expected, given=response.body)
        fixture.destroy_repo(fork_name)

    def test_api_fork_repo_unknown_owner(self):
        fork_name = 'api-repo-fork'
        owner = 'i-dont-exist'
        id_, params = _build_data(self.apikey, 'fork_repo',
                                  repoid=self.REPO,
                                  fork_name=fork_name,
                                  owner=owner,
        )
        response = api_call(self, params)
        expected = 'user `%s` does not exist' % owner
        self._compare_error(id_, expected, given=response.body)

    def test_api_fork_repo_fork_exists(self):
        fork_name = 'api-repo-fork'
        fixture.create_fork(self.REPO, fork_name)

        try:
            fork_name = 'api-repo-fork'

            id_, params = _build_data(self.apikey, 'fork_repo',
                                      repoid=self.REPO,
                                      fork_name=fork_name,
                                      owner=TEST_USER_ADMIN_LOGIN,
            )
            response = api_call(self, params)

            expected = "fork `%s` already exist" % fork_name
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_repo(fork_name)

    def test_api_fork_repo_repo_exists(self):
        fork_name = self.REPO

        id_, params = _build_data(self.apikey, 'fork_repo',
                                  repoid=self.REPO,
                                  fork_name=fork_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
        )
        response = api_call(self, params)

        expected = "repo `%s` already exist" % fork_name
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoModel, 'create_fork', crash)
    def test_api_fork_repo_exception_occurred(self):
        fork_name = 'api-repo-fork'
        id_, params = _build_data(self.apikey, 'fork_repo',
                                  repoid=self.REPO,
                                  fork_name=fork_name,
                                  owner=TEST_USER_ADMIN_LOGIN,
        )
        response = api_call(self, params)

        expected = 'failed to fork repository `%s` as `%s`' % (self.REPO,
                                                               fork_name)
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_user_group(self):
        id_, params = _build_data(self.apikey, 'get_user_group',
                                  usergroupid=TEST_USER_GROUP)
        response = api_call(self, params)

        user_group = UserGroupModel().get_group(TEST_USER_GROUP)
        members = []
        for user in user_group.members:
            user = user.user
            members.append(user.get_api_data())

        ret = user_group.get_api_data()
        ret['members'] = members
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_user_groups(self):
        gr_name = 'test_user_group2'
        make_user_group(gr_name)

        id_, params = _build_data(self.apikey, 'get_user_groups', )
        response = api_call(self, params)

        try:
            expected = []
            for gr_name in [TEST_USER_GROUP, 'test_user_group2']:
                user_group = UserGroupModel().get_group(gr_name)
                ret = user_group.get_api_data()
                expected.append(ret)
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_user_group(gr_name)

    def test_api_create_user_group(self):
        group_name = 'some_new_group'
        id_, params = _build_data(self.apikey, 'create_user_group',
                                  group_name=group_name)
        response = api_call(self, params)

        ret = {
            'msg': 'created new user group `%s`' % group_name,
            'user_group': jsonify(UserGroupModel() \
                .get_by_name(group_name) \
                .get_api_data())
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

        fixture.destroy_user_group(group_name)

    def test_api_get_user_group_that_exist(self):
        id_, params = _build_data(self.apikey, 'create_user_group',
                                  group_name=TEST_USER_GROUP)
        response = api_call(self, params)

        expected = "user group `%s` already exist" % TEST_USER_GROUP
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(UserGroupModel, 'create', crash)
    def test_api_get_user_group_exception_occurred(self):
        group_name = 'exception_happens'
        id_, params = _build_data(self.apikey, 'create_user_group',
                                  group_name=group_name)
        response = api_call(self, params)

        expected = 'failed to create group `%s`' % group_name
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([('group_name', {'group_name': 'new_group_name'}),
                           ('group_name', {'group_name': 'test_group_for_update'}),
                           ('owner', {'owner': TEST_USER_REGULAR_LOGIN}),
                           ('active', {'active': False}),
                           ('active', {'active': True})])
    def test_api_update_user_group(self, changing_attr, updates):
        gr_name = 'test_group_for_update'
        user_group = fixture.create_user_group(gr_name)
        id_, params = _build_data(self.apikey, 'update_user_group',
                                  usergroupid=gr_name, **updates)
        response = api_call(self, params)
        try:
            expected = {
               'msg': 'updated user group ID:%s %s' % (user_group.users_group_id,
                                                     user_group.users_group_name),
               'user_group': user_group.get_api_data()
            }
            self._compare_ok(id_, expected, given=response.body)
        finally:
            if changing_attr == 'group_name':
                # switch to updated name for proper cleanup
                gr_name = updates['group_name']
            fixture.destroy_user_group(gr_name)

    @mock.patch.object(UserGroupModel, 'update', crash)
    def test_api_update_user_group_exception_occured(self):
        gr_name = 'test_group'
        fixture.create_user_group(gr_name)
        id_, params = _build_data(self.apikey, 'update_user_group',
                                  usergroupid=gr_name)
        response = api_call(self, params)
        try:
            expected = 'failed to update user group `%s`' % gr_name
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_user_group(gr_name)

    def test_api_add_user_to_user_group(self):
        gr_name = 'test_group'
        fixture.create_user_group(gr_name)
        id_, params = _build_data(self.apikey, 'add_user_to_user_group',
                                  usergroupid=gr_name,
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)
        try:
            expected = {
            'msg': 'added member `%s` to user group `%s`' % (
                    TEST_USER_ADMIN_LOGIN, gr_name),
            'success': True
            }
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_user_group(gr_name)

    def test_api_add_user_to_user_group_that_doesnt_exist(self):
        id_, params = _build_data(self.apikey, 'add_user_to_user_group',
                                  usergroupid='false-group',
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)

        expected = 'user group `%s` does not exist' % 'false-group'
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(UserGroupModel, 'add_user_to_group', crash)
    def test_api_add_user_to_user_group_exception_occurred(self):
        gr_name = 'test_group'
        fixture.create_user_group(gr_name)
        id_, params = _build_data(self.apikey, 'add_user_to_user_group',
                                  usergroupid=gr_name,
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)

        try:
            expected = 'failed to add member to user group `%s`' % gr_name
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_user_group(gr_name)

    def test_api_remove_user_from_user_group(self):
        gr_name = 'test_group_3'
        gr = fixture.create_user_group(gr_name)
        UserGroupModel().add_user_to_group(gr, user=TEST_USER_ADMIN_LOGIN)
        Session().commit()
        id_, params = _build_data(self.apikey, 'remove_user_from_user_group',
                                  usergroupid=gr_name,
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)

        try:
            expected = {
                'msg': 'removed member `%s` from user group `%s`' % (
                    TEST_USER_ADMIN_LOGIN, gr_name
                ),
                'success': True}
            self._compare_ok(id_, expected, given=response.body)
        finally:
            fixture.destroy_user_group(gr_name)

    @mock.patch.object(UserGroupModel, 'remove_user_from_group', crash)
    def test_api_remove_user_from_user_group_exception_occurred(self):
        gr_name = 'test_group_3'
        gr = fixture.create_user_group(gr_name)
        UserGroupModel().add_user_to_group(gr, user=TEST_USER_ADMIN_LOGIN)
        Session().commit()
        id_, params = _build_data(self.apikey, 'remove_user_from_user_group',
                                  usergroupid=gr_name,
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)
        try:
            expected = 'failed to remove member from user group `%s`' % gr_name
            self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_user_group(gr_name)

    def test_api_delete_user_group(self):
        gr_name = 'test_group'
        ugroup = fixture.create_user_group(gr_name)
        gr_id = ugroup.users_group_id
        id_, params = _build_data(self.apikey, 'delete_user_group',
                                  usergroupid=gr_name,
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)

        try:
            expected = {
                'user_group': None,
                'msg': 'deleted user group ID:%s %s' % (gr_id, gr_name)
            }
            self._compare_ok(id_, expected, given=response.body)
        finally:
            if UserGroupModel().get_by_name(gr_name):
                fixture.destroy_user_group(gr_name)

    def test_api_delete_user_group_that_is_assigned(self):
        gr_name = 'test_group'
        ugroup = fixture.create_user_group(gr_name)
        gr_id = ugroup.users_group_id

        ugr_to_perm = RepoModel().grant_user_group_permission(self.REPO, gr_name, 'repository.write')
        msg = 'RepoGroup assigned to [%s]' % (ugr_to_perm)

        id_, params = _build_data(self.apikey, 'delete_user_group',
                                  usergroupid=gr_name,
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)

        try:
            expected = msg
            self._compare_error(id_, expected, given=response.body)
        finally:
            if UserGroupModel().get_by_name(gr_name):
                fixture.destroy_user_group(gr_name)

    def test_api_delete_user_group_exception_occured(self):
        gr_name = 'test_group'
        ugroup = fixture.create_user_group(gr_name)
        gr_id = ugroup.users_group_id
        id_, params = _build_data(self.apikey, 'delete_user_group',
                                  usergroupid=gr_name,
                                  userid=TEST_USER_ADMIN_LOGIN)

        try:
            with mock.patch.object(UserGroupModel, 'delete', crash):
                response = api_call(self, params)
                expected = 'failed to delete user group ID:%s %s' % (gr_id, gr_name)
                self._compare_error(id_, expected, given=response.body)
        finally:
            fixture.destroy_user_group(gr_name)

    @parameterized.expand([('none', 'repository.none'),
                           ('read', 'repository.read'),
                           ('write', 'repository.write'),
                           ('admin', 'repository.admin')])
    def test_api_grant_user_permission(self, name, perm):
        id_, params = _build_data(self.apikey,
                                  'grant_user_permission',
                                  repoid=self.REPO,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  perm=perm)
        response = api_call(self, params)

        ret = {
            'msg': 'Granted perm: `%s` for user: `%s` in repo: `%s`' % (
                perm, TEST_USER_ADMIN_LOGIN, self.REPO
            ),
            'success': True
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_grant_user_permission_wrong_permission(self):
        perm = 'haha.no.permission'
        id_, params = _build_data(self.apikey,
                                  'grant_user_permission',
                                  repoid=self.REPO,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'permission `%s` does not exist' % perm
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoModel, 'grant_user_permission', crash)
    def test_api_grant_user_permission_exception_when_adding(self):
        perm = 'repository.read'
        id_, params = _build_data(self.apikey,
                                  'grant_user_permission',
                                  repoid=self.REPO,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'failed to edit permission for user: `%s` in repo: `%s`' % (
            TEST_USER_ADMIN_LOGIN, self.REPO
        )
        self._compare_error(id_, expected, given=response.body)

    def test_api_revoke_user_permission(self):
        id_, params = _build_data(self.apikey,
                                  'revoke_user_permission',
                                  repoid=self.REPO,
                                  userid=TEST_USER_ADMIN_LOGIN, )
        response = api_call(self, params)

        expected = {
            'msg': 'Revoked perm for user: `%s` in repo: `%s`' % (
                TEST_USER_ADMIN_LOGIN, self.REPO
            ),
            'success': True
        }
        self._compare_ok(id_, expected, given=response.body)

    @mock.patch.object(RepoModel, 'revoke_user_permission', crash)
    def test_api_revoke_user_permission_exception_when_adding(self):
        id_, params = _build_data(self.apikey,
                                  'revoke_user_permission',
                                  repoid=self.REPO,
                                  userid=TEST_USER_ADMIN_LOGIN, )
        response = api_call(self, params)

        expected = 'failed to edit permission for user: `%s` in repo: `%s`' % (
            TEST_USER_ADMIN_LOGIN, self.REPO
        )
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([('none', 'repository.none'),
                           ('read', 'repository.read'),
                           ('write', 'repository.write'),
                           ('admin', 'repository.admin')])
    def test_api_grant_user_group_permission(self, name, perm):
        id_, params = _build_data(self.apikey,
                                  'grant_user_group_permission',
                                  repoid=self.REPO,
                                  usergroupid=TEST_USER_GROUP,
                                  perm=perm)
        response = api_call(self, params)

        ret = {
            'msg': 'Granted perm: `%s` for user group: `%s` in repo: `%s`' % (
                perm, TEST_USER_GROUP, self.REPO
            ),
            'success': True
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    def test_api_grant_user_group_permission_wrong_permission(self):
        perm = 'haha.no.permission'
        id_, params = _build_data(self.apikey,
                                  'grant_user_group_permission',
                                  repoid=self.REPO,
                                  usergroupid=TEST_USER_GROUP,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'permission `%s` does not exist' % perm
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoModel, 'grant_user_group_permission', crash)
    def test_api_grant_user_group_permission_exception_when_adding(self):
        perm = 'repository.read'
        id_, params = _build_data(self.apikey,
                                  'grant_user_group_permission',
                                  repoid=self.REPO,
                                  usergroupid=TEST_USER_GROUP,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'failed to edit permission for user group: `%s` in repo: `%s`' % (
            TEST_USER_GROUP, self.REPO
        )
        self._compare_error(id_, expected, given=response.body)

    def test_api_revoke_user_group_permission(self):
        RepoModel().grant_user_group_permission(repo=self.REPO,
                                                group_name=TEST_USER_GROUP,
                                                perm='repository.read')
        Session().commit()
        id_, params = _build_data(self.apikey,
                                  'revoke_user_group_permission',
                                  repoid=self.REPO,
                                  usergroupid=TEST_USER_GROUP, )
        response = api_call(self, params)

        expected = {
            'msg': 'Revoked perm for user group: `%s` in repo: `%s`' % (
                TEST_USER_GROUP, self.REPO
            ),
            'success': True
        }
        self._compare_ok(id_, expected, given=response.body)

    @mock.patch.object(RepoModel, 'revoke_user_group_permission', crash)
    def test_api_revoke_user_group_permission_exception_when_adding(self):
        id_, params = _build_data(self.apikey,
                                  'revoke_user_group_permission',
                                  repoid=self.REPO,
                                  usergroupid=TEST_USER_GROUP, )
        response = api_call(self, params)

        expected = 'failed to edit permission for user group: `%s` in repo: `%s`' % (
            TEST_USER_GROUP, self.REPO
        )
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([
        ('none', 'group.none', 'none'),
        ('read', 'group.read', 'none'),
        ('write', 'group.write', 'none'),
        ('admin', 'group.admin', 'none'),

        ('none', 'group.none', 'all'),
        ('read', 'group.read', 'all'),
        ('write', 'group.write', 'all'),
        ('admin', 'group.admin', 'all'),

        ('none', 'group.none', 'repos'),
        ('read', 'group.read', 'repos'),
        ('write', 'group.write', 'repos'),
        ('admin', 'group.admin', 'repos'),

        ('none', 'group.none', 'groups'),
        ('read', 'group.read', 'groups'),
        ('write', 'group.write', 'groups'),
        ('admin', 'group.admin', 'groups'),
    ])
    def test_api_grant_user_permission_to_repo_group(self, name, perm, apply_to_children):
        id_, params = _build_data(self.apikey,
                                  'grant_user_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  perm=perm, apply_to_children=apply_to_children)
        response = api_call(self, params)

        ret = {
            'msg': 'Granted perm: `%s` (recursive:%s) for user: `%s` in repo group: `%s`' % (
                perm, apply_to_children, TEST_USER_ADMIN_LOGIN, TEST_REPO_GROUP
            ),
            'success': True
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    @parameterized.expand([
        ('none_fails', 'group.none', 'none', False, False),
        ('read_fails', 'group.read', 'none', False, False),
        ('write_fails', 'group.write', 'none', False, False),
        ('admin_fails', 'group.admin', 'none', False, False),

        # with granted perms
        ('none_ok', 'group.none', 'none', True, True),
        ('read_ok', 'group.read', 'none', True, True),
        ('write_ok', 'group.write', 'none', True, True),
        ('admin_ok', 'group.admin', 'none', True, True),
    ])
    def test_api_grant_user_permission_to_repo_group_by_regular_user(
            self, name, perm, apply_to_children, grant_admin, access_ok):
        if grant_admin:
            RepoGroupModel().grant_user_permission(TEST_REPO_GROUP,
                                                   self.TEST_USER_LOGIN,
                                                   'group.admin')
            Session().commit()

        id_, params = _build_data(self.apikey_regular,
                                  'grant_user_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  perm=perm, apply_to_children=apply_to_children)
        response = api_call(self, params)
        if access_ok:
            ret = {
                'msg': 'Granted perm: `%s` (recursive:%s) for user: `%s` in repo group: `%s`' % (
                    perm, apply_to_children, TEST_USER_ADMIN_LOGIN, TEST_REPO_GROUP
                ),
                'success': True
            }
            expected = ret
            self._compare_ok(id_, expected, given=response.body)
        else:
            expected = 'repository group `%s` does not exist' % TEST_REPO_GROUP
            self._compare_error(id_, expected, given=response.body)

    def test_api_grant_user_permission_to_repo_group_wrong_permission(self):
        perm = 'haha.no.permission'
        id_, params = _build_data(self.apikey,
                                  'grant_user_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'permission `%s` does not exist' % perm
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoGroupModel, 'grant_user_permission', crash)
    def test_api_grant_user_permission_to_repo_group_exception_when_adding(self):
        perm = 'group.read'
        id_, params = _build_data(self.apikey,
                                  'grant_user_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'failed to edit permission for user: `%s` in repo group: `%s`' % (
            TEST_USER_ADMIN_LOGIN, TEST_REPO_GROUP
        )
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([
        ('none', 'none'),
        ('all', 'all'),
        ('repos', 'repos'),
        ('groups', 'groups'),
    ])
    def test_api_revoke_user_permission_from_repo_group(self, name, apply_to_children):
        RepoGroupModel().grant_user_permission(repo_group=TEST_REPO_GROUP,
                                               user=TEST_USER_ADMIN_LOGIN,
                                               perm='group.read',)
        Session().commit()

        id_, params = _build_data(self.apikey,
                                  'revoke_user_permission_from_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  apply_to_children=apply_to_children,)
        response = api_call(self, params)

        expected = {
            'msg': 'Revoked perm (recursive:%s) for user: `%s` in repo group: `%s`' % (
                apply_to_children, TEST_USER_ADMIN_LOGIN, TEST_REPO_GROUP
            ),
            'success': True
        }
        self._compare_ok(id_, expected, given=response.body)

    @parameterized.expand([
        ('none', 'none', False, False),
        ('all', 'all', False, False),
        ('repos', 'repos', False, False),
        ('groups', 'groups', False, False),

        # after granting admin rights
        ('none', 'none', False, False),
        ('all', 'all', False, False),
        ('repos', 'repos', False, False),
        ('groups', 'groups', False, False),
    ])
    def test_api_revoke_user_permission_from_repo_group_by_regular_user(
            self, name, apply_to_children, grant_admin, access_ok):
        RepoGroupModel().grant_user_permission(repo_group=TEST_REPO_GROUP,
                                               user=TEST_USER_ADMIN_LOGIN,
                                               perm='group.read',)
        Session().commit()

        if grant_admin:
            RepoGroupModel().grant_user_permission(TEST_REPO_GROUP,
                                                   self.TEST_USER_LOGIN,
                                                   'group.admin')
            Session().commit()

        id_, params = _build_data(self.apikey_regular,
                                  'revoke_user_permission_from_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  userid=TEST_USER_ADMIN_LOGIN,
                                  apply_to_children=apply_to_children,)
        response = api_call(self, params)
        if access_ok:
            expected = {
                'msg': 'Revoked perm (recursive:%s) for user: `%s` in repo group: `%s`' % (
                    apply_to_children, TEST_USER_ADMIN_LOGIN, TEST_REPO_GROUP
                ),
                'success': True
            }
            self._compare_ok(id_, expected, given=response.body)
        else:
            expected = 'repository group `%s` does not exist' % TEST_REPO_GROUP
            self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoGroupModel, 'revoke_user_permission', crash)
    def test_api_revoke_user_permission_from_repo_group_exception_when_adding(self):
        id_, params = _build_data(self.apikey,
                                  'revoke_user_permission_from_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  userid=TEST_USER_ADMIN_LOGIN, )
        response = api_call(self, params)

        expected = 'failed to edit permission for user: `%s` in repo group: `%s`' % (
            TEST_USER_ADMIN_LOGIN, TEST_REPO_GROUP
        )
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([
        ('none', 'group.none', 'none'),
        ('read', 'group.read', 'none'),
        ('write', 'group.write', 'none'),
        ('admin', 'group.admin', 'none'),

        ('none', 'group.none', 'all'),
        ('read', 'group.read', 'all'),
        ('write', 'group.write', 'all'),
        ('admin', 'group.admin', 'all'),

        ('none', 'group.none', 'repos'),
        ('read', 'group.read', 'repos'),
        ('write', 'group.write', 'repos'),
        ('admin', 'group.admin', 'repos'),

        ('none', 'group.none', 'groups'),
        ('read', 'group.read', 'groups'),
        ('write', 'group.write', 'groups'),
        ('admin', 'group.admin', 'groups'),
    ])
    def test_api_grant_user_group_permission_to_repo_group(self, name, perm, apply_to_children):
        id_, params = _build_data(self.apikey,
                                  'grant_user_group_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  usergroupid=TEST_USER_GROUP,
                                  perm=perm,
                                  apply_to_children=apply_to_children,)
        response = api_call(self, params)

        ret = {
            'msg': 'Granted perm: `%s` (recursive:%s) for user group: `%s` in repo group: `%s`' % (
                perm, apply_to_children, TEST_USER_GROUP, TEST_REPO_GROUP
            ),
            'success': True
        }
        expected = ret
        self._compare_ok(id_, expected, given=response.body)

    @parameterized.expand([
        ('none_fails', 'group.none', 'none', False, False),
        ('read_fails', 'group.read', 'none', False, False),
        ('write_fails', 'group.write', 'none', False, False),
        ('admin_fails', 'group.admin', 'none', False, False),

        # with granted perms
        ('none_ok', 'group.none', 'none', True, True),
        ('read_ok', 'group.read', 'none', True, True),
        ('write_ok', 'group.write', 'none', True, True),
        ('admin_ok', 'group.admin', 'none', True, True),
    ])
    def test_api_grant_user_group_permission_to_repo_group_by_regular_user(
            self, name, perm, apply_to_children, grant_admin, access_ok):
        if grant_admin:
            RepoGroupModel().grant_user_permission(TEST_REPO_GROUP,
                                                   self.TEST_USER_LOGIN,
                                                   'group.admin')
            Session().commit()

        id_, params = _build_data(self.apikey_regular,
                                  'grant_user_group_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  usergroupid=TEST_USER_GROUP,
                                  perm=perm,
                                  apply_to_children=apply_to_children,)
        response = api_call(self, params)
        if access_ok:
            ret = {
                'msg': 'Granted perm: `%s` (recursive:%s) for user group: `%s` in repo group: `%s`' % (
                    perm, apply_to_children, TEST_USER_GROUP, TEST_REPO_GROUP
                ),
                'success': True
            }
            expected = ret
            self._compare_ok(id_, expected, given=response.body)
        else:
            expected = 'repository group `%s` does not exist' % TEST_REPO_GROUP
            self._compare_error(id_, expected, given=response.body)

    def test_api_grant_user_group_permission_to_repo_group_wrong_permission(self):
        perm = 'haha.no.permission'
        id_, params = _build_data(self.apikey,
                                  'grant_user_group_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  usergroupid=TEST_USER_GROUP,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'permission `%s` does not exist' % perm
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoGroupModel, 'grant_user_group_permission', crash)
    def test_api_grant_user_group_permission_exception_when_adding(self):
        perm = 'group.read'
        id_, params = _build_data(self.apikey,
                                  'grant_user_group_permission_to_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  usergroupid=TEST_USER_GROUP,
                                  perm=perm)
        response = api_call(self, params)

        expected = 'failed to edit permission for user group: `%s` in repo group: `%s`' % (
            TEST_USER_GROUP, TEST_REPO_GROUP
        )
        self._compare_error(id_, expected, given=response.body)

    @parameterized.expand([
        ('none', 'none'),
        ('all', 'all'),
        ('repos', 'repos'),
        ('groups', 'groups'),
    ])
    def test_api_revoke_user_group_permission_from_repo_group(self, name, apply_to_children):
        RepoGroupModel().grant_user_group_permission(repo_group=TEST_REPO_GROUP,
                                                     group_name=TEST_USER_GROUP,
                                                     perm='group.read',)
        Session().commit()
        id_, params = _build_data(self.apikey,
                                  'revoke_user_group_permission_from_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  usergroupid=TEST_USER_GROUP,
                                  apply_to_children=apply_to_children,)
        response = api_call(self, params)

        expected = {
            'msg': 'Revoked perm (recursive:%s) for user group: `%s` in repo group: `%s`' % (
                apply_to_children, TEST_USER_GROUP, TEST_REPO_GROUP
            ),
            'success': True
        }
        self._compare_ok(id_, expected, given=response.body)

    @parameterized.expand([
        ('none', 'none', False, False),
        ('all', 'all', False, False),
        ('repos', 'repos', False, False),
        ('groups', 'groups', False, False),

        # after granting admin rights
        ('none', 'none', False, False),
        ('all', 'all', False, False),
        ('repos', 'repos', False, False),
        ('groups', 'groups', False, False),
    ])
    def test_api_revoke_user_group_permission_from_repo_group_by_regular_user(
            self, name, apply_to_children, grant_admin, access_ok):
        RepoGroupModel().grant_user_permission(repo_group=TEST_REPO_GROUP,
                                               user=TEST_USER_ADMIN_LOGIN,
                                               perm='group.read',)
        Session().commit()

        if grant_admin:
            RepoGroupModel().grant_user_permission(TEST_REPO_GROUP,
                                                   self.TEST_USER_LOGIN,
                                                   'group.admin')
            Session().commit()

        id_, params = _build_data(self.apikey_regular,
                                  'revoke_user_group_permission_from_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  usergroupid=TEST_USER_GROUP,
                                  apply_to_children=apply_to_children,)
        response = api_call(self, params)
        if access_ok:
            expected = {
                'msg': 'Revoked perm (recursive:%s) for user group: `%s` in repo group: `%s`' % (
                    apply_to_children, TEST_USER_ADMIN_LOGIN, TEST_REPO_GROUP
                ),
                'success': True
            }
            self._compare_ok(id_, expected, given=response.body)
        else:
            expected = 'repository group `%s` does not exist' % TEST_REPO_GROUP
            self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(RepoGroupModel, 'revoke_user_group_permission', crash)
    def test_api_revoke_user_group_permission_from_repo_group_exception_when_adding(self):
        id_, params = _build_data(self.apikey, 'revoke_user_group_permission_from_repo_group',
                                  repogroupid=TEST_REPO_GROUP,
                                  usergroupid=TEST_USER_GROUP,)
        response = api_call(self, params)

        expected = 'failed to edit permission for user group: `%s` in repo group: `%s`' % (
            TEST_USER_GROUP, TEST_REPO_GROUP
        )
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_gist(self):
        gist = fixture.create_gist()
        gist_id = gist.gist_access_id
        gist_created_on = gist.created_on
        id_, params = _build_data(self.apikey, 'get_gist',
                                  gistid=gist_id, )
        response = api_call(self, params)

        expected = {
            'access_id': gist_id,
            'created_on': gist_created_on,
            'description': 'new-gist',
            'expires': -1.0,
            'gist_id': int(gist_id),
            'type': 'public',
            'url': 'http://localhost:80/_admin/gists/%s' % gist_id
        }

        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_gist_that_does_not_exist(self):
        id_, params = _build_data(self.apikey_regular, 'get_gist',
                                  gistid='12345', )
        response = api_call(self, params)
        expected = 'gist `%s` does not exist' % ('12345',)
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_gist_private_gist_without_permission(self):
        gist = fixture.create_gist()
        gist_id = gist.gist_access_id
        gist_created_on = gist.created_on
        id_, params = _build_data(self.apikey_regular, 'get_gist',
                                  gistid=gist_id, )
        response = api_call(self, params)

        expected = 'gist `%s` does not exist' % gist_id
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_gists(self):
        fixture.create_gist()
        fixture.create_gist()

        id_, params = _build_data(self.apikey, 'get_gists')
        response = api_call(self, params)
        expected = response.json
        self.assertEqual(len(response.json['result']), 2)
        #self._compare_ok(id_, expected, given=response.body)

    def test_api_get_gists_regular_user(self):
        # by admin
        fixture.create_gist()
        fixture.create_gist()

        # by reg user
        fixture.create_gist(owner=self.TEST_USER_LOGIN)
        fixture.create_gist(owner=self.TEST_USER_LOGIN)
        fixture.create_gist(owner=self.TEST_USER_LOGIN)

        id_, params = _build_data(self.apikey_regular, 'get_gists')
        response = api_call(self, params)
        expected = response.json
        self.assertEqual(len(response.json['result']), 3)
        #self._compare_ok(id_, expected, given=response.body)

    def test_api_get_gists_only_for_regular_user(self):
        # by admin
        fixture.create_gist()
        fixture.create_gist()

        # by reg user
        fixture.create_gist(owner=self.TEST_USER_LOGIN)
        fixture.create_gist(owner=self.TEST_USER_LOGIN)
        fixture.create_gist(owner=self.TEST_USER_LOGIN)

        id_, params = _build_data(self.apikey, 'get_gists',
                                  userid=self.TEST_USER_LOGIN)
        response = api_call(self, params)
        expected = response.json
        self.assertEqual(len(response.json['result']), 3)
        #self._compare_ok(id_, expected, given=response.body)

    def test_api_get_gists_regular_user_with_different_userid(self):
        id_, params = _build_data(self.apikey_regular, 'get_gists',
                                  userid=TEST_USER_ADMIN_LOGIN)
        response = api_call(self, params)
        expected = 'userid is not the same as your user'
        self._compare_error(id_, expected, given=response.body)

    def test_api_create_gist(self):
        id_, params = _build_data(self.apikey_regular, 'create_gist',
                                  lifetime=10,
                                  description='foobar-gist',
                                  gist_type='public',
                                  files={'foobar': {'content': 'foo'}})
        response = api_call(self, params)
        response_json = response.json
        expected = {
            'gist': {
                'access_id': response_json['result']['gist']['access_id'],
                'created_on': response_json['result']['gist']['created_on'],
                'description': 'foobar-gist',
                'expires': response_json['result']['gist']['expires'],
                'gist_id': response_json['result']['gist']['gist_id'],
                'type': 'public',
                'url': response_json['result']['gist']['url']
            },
            'msg': 'created new gist'
        }
        self._compare_ok(id_, expected, given=response.body)

    @mock.patch.object(GistModel, 'create', crash)
    def test_api_create_gist_exception_occured(self):
        id_, params = _build_data(self.apikey_regular, 'create_gist',
                                  files={})
        response = api_call(self, params)
        expected = 'failed to create gist'
        self._compare_error(id_, expected, given=response.body)

    def test_api_delete_gist(self):
        gist_id = fixture.create_gist().gist_access_id
        id_, params = _build_data(self.apikey, 'delete_gist',
                                  gistid=gist_id)
        response = api_call(self, params)
        expected = {'gist': None, 'msg': 'deleted gist ID:%s' % gist_id}
        self._compare_ok(id_, expected, given=response.body)

    def test_api_delete_gist_regular_user(self):
        gist_id = fixture.create_gist(owner=self.TEST_USER_LOGIN).gist_access_id
        id_, params = _build_data(self.apikey_regular, 'delete_gist',
                                  gistid=gist_id)
        response = api_call(self, params)
        expected = {'gist': None, 'msg': 'deleted gist ID:%s' % gist_id}
        self._compare_ok(id_, expected, given=response.body)

    def test_api_delete_gist_regular_user_no_permission(self):
        gist_id = fixture.create_gist().gist_access_id
        id_, params = _build_data(self.apikey_regular, 'delete_gist',
                                  gistid=gist_id)
        response = api_call(self, params)
        expected = 'gist `%s` does not exist' % (gist_id,)
        self._compare_error(id_, expected, given=response.body)

    @mock.patch.object(GistModel, 'delete', crash)
    def test_api_delete_gist_exception_occured(self):
        gist_id = fixture.create_gist().gist_access_id
        id_, params = _build_data(self.apikey, 'delete_gist',
                                  gistid=gist_id)
        response = api_call(self, params)
        expected = 'failed to delete gist ID:%s' % (gist_id,)
        self._compare_error(id_, expected, given=response.body)

    def test_api_get_ip(self):
        id_, params = _build_data(self.apikey, 'get_ip')
        response = api_call(self, params)
        expected = {
            'server_ip_addr': '0.0.0.0',
            'user_ips': []
        }
        self._compare_ok(id_, expected, given=response.body)

    def test_api_get_server_info(self):
        id_, params = _build_data(self.apikey, 'get_server_info')
        response = api_call(self, params)
        expected = Setting.get_server_info()
        self._compare_ok(id_, expected, given=response.body)
