# -*- coding: utf-8 -*-

import os
import mock
import urllib

from kallithea.lib import vcs
from kallithea.model.db import Repository, RepoGroup, UserRepoToPerm, User,\
    Permission
from kallithea.model.user import UserModel
from kallithea.tests import *
from kallithea.model.repo_group import RepoGroupModel
from kallithea.model.repo import RepoModel
from kallithea.model.meta import Session
from kallithea.tests.fixture import Fixture, error_function

fixture = Fixture()


def _get_permission_for_user(user, repo):
    perm = UserRepoToPerm.query()\
                .filter(UserRepoToPerm.repository ==
                        Repository.get_by_repo_name(repo))\
                .filter(UserRepoToPerm.user == User.get_by_username(user))\
                .all()
    return perm


class _BaseTest(TestController):
    """
    Write all tests here
    """
    REPO = None
    REPO_TYPE = None
    NEW_REPO = None
    OTHER_TYPE_REPO = None
    OTHER_TYPE = None

    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def test_index(self):
        self.log_user()
        response = self.app.get(url('repos'))

    def test_create(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name))
        self.assertEqual(response.json, {u'result': True})
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name, repo_name))

        # test if the repo was created in the database
        new_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name).one()

        self.assertEqual(new_repo.repo_name, repo_name)
        self.assertEqual(new_repo.description, description)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name))
        response.mustcontain(repo_name)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(os.path.join(TESTS_TMP_PATH, repo_name))
        except Exception:
            self.fail('no repo %s in filesystem' % repo_name)

        RepoModel().delete(repo_name)
        Session().commit()

    def test_create_non_ascii(self):
        self.log_user()
        non_ascii = "ąęł"
        repo_name = "%s%s" % (self.NEW_REPO, non_ascii)
        repo_name_unicode = repo_name.decode('utf8')
        description = 'description for newly created repo' + non_ascii
        description_unicode = description.decode('utf8')
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name))
        self.assertEqual(response.json, {u'result': True})
        self.checkSessionFlash(response,
                               u'Created repository <a href="/%s">%s</a>'
                               % (urllib.quote(repo_name), repo_name_unicode))
        # test if the repo was created in the database
        new_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name_unicode).one()

        self.assertEqual(new_repo.repo_name, repo_name_unicode)
        self.assertEqual(new_repo.description, description_unicode)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name))
        response.mustcontain(repo_name)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(os.path.join(TESTS_TMP_PATH, repo_name))
        except Exception:
            self.fail('no repo %s in filesystem' % repo_name)

    def test_create_in_group(self):
        self.log_user()

        ## create GROUP
        group_name = 'sometest_%s' % self.REPO_TYPE
        gr = RepoGroupModel().create(group_name=group_name,
                                     group_description='test',
                                     owner=TEST_USER_ADMIN_LOGIN)
        Session().commit()

        repo_name = 'ingroup'
        repo_name_full = RepoGroup.url_sep().join([group_name, repo_name])
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr.group_id,))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name_full))
        self.assertEqual(response.json, {u'result': True})
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name_full, repo_name_full))
        # test if the repo was created in the database
        new_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name_full).one()
        new_repo_id = new_repo.repo_id

        self.assertEqual(new_repo.repo_name, repo_name_full)
        self.assertEqual(new_repo.description, description)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name_full))
        response.mustcontain(repo_name_full)
        response.mustcontain(self.REPO_TYPE)

        inherited_perms = UserRepoToPerm.query()\
            .filter(UserRepoToPerm.repository_id == new_repo_id).all()
        self.assertEqual(len(inherited_perms), 1)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(os.path.join(TESTS_TMP_PATH, repo_name_full))
        except Exception:
            RepoGroupModel().delete(group_name)
            Session().commit()
            self.fail('no repo %s in filesystem' % repo_name)

        RepoModel().delete(repo_name_full)
        RepoGroupModel().delete(group_name)
        Session().commit()

    def test_create_in_group_without_needed_permissions(self):
        usr = self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        # revoke
        user_model = UserModel()
        # disable fork and create on default user
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.create.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.create.none')
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.fork.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.fork.none')

        # disable on regular user
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.none')
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.none')
        Session().commit()

        ## create GROUP
        group_name = 'reg_sometest_%s' % self.REPO_TYPE
        gr = RepoGroupModel().create(group_name=group_name,
                                     group_description='test',
                                     owner=TEST_USER_ADMIN_LOGIN)
        Session().commit()

        group_name_allowed = 'reg_sometest_allowed_%s' % self.REPO_TYPE
        gr_allowed = RepoGroupModel().create(group_name=group_name_allowed,
                                     group_description='test',
                                     owner=TEST_USER_REGULAR_LOGIN)
        Session().commit()

        repo_name = 'ingroup'
        repo_name_full = RepoGroup.url_sep().join([group_name, repo_name])
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr.group_id,))

        response.mustcontain('Invalid value')

        # user is allowed to create in this group
        repo_name = 'ingroup'
        repo_name_full = RepoGroup.url_sep().join([group_name_allowed, repo_name])
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr_allowed.group_id,))

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name_full))
        self.assertEqual(response.json, {u'result': True})
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name_full, repo_name_full))
        # test if the repo was created in the database
        new_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name_full).one()
        new_repo_id = new_repo.repo_id

        self.assertEqual(new_repo.repo_name, repo_name_full)
        self.assertEqual(new_repo.description, description)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name_full))
        response.mustcontain(repo_name_full)
        response.mustcontain(self.REPO_TYPE)

        inherited_perms = UserRepoToPerm.query()\
            .filter(UserRepoToPerm.repository_id == new_repo_id).all()
        self.assertEqual(len(inherited_perms), 1)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(os.path.join(TESTS_TMP_PATH, repo_name_full))
        except Exception:
            RepoGroupModel().delete(group_name)
            Session().commit()
            self.fail('no repo %s in filesystem' % repo_name)

        RepoModel().delete(repo_name_full)
        RepoGroupModel().delete(group_name)
        RepoGroupModel().delete(group_name_allowed)
        Session().commit()

    def test_create_in_group_inherit_permissions(self):
        self.log_user()

        ## create GROUP
        group_name = 'sometest_%s' % self.REPO_TYPE
        gr = RepoGroupModel().create(group_name=group_name,
                                     group_description='test',
                                     owner=TEST_USER_ADMIN_LOGIN)
        perm = Permission.get_by_key('repository.write')
        RepoGroupModel().grant_user_permission(gr, TEST_USER_REGULAR_LOGIN, perm)

        ## add repo permissions
        Session().commit()

        repo_name = 'ingroup_inherited_%s' % self.REPO_TYPE
        repo_name_full = RepoGroup.url_sep().join([group_name, repo_name])
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                repo_group=gr.group_id,
                                                repo_copy_permissions=True))

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name_full))
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name_full, repo_name_full))
        # test if the repo was created in the database
        new_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name_full).one()
        new_repo_id = new_repo.repo_id

        self.assertEqual(new_repo.repo_name, repo_name_full)
        self.assertEqual(new_repo.description, description)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name_full))
        response.mustcontain(repo_name_full)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(os.path.join(TESTS_TMP_PATH, repo_name_full))
        except Exception:
            RepoGroupModel().delete(group_name)
            Session().commit()
            self.fail('no repo %s in filesystem' % repo_name)

        #check if inherited permissiona are applied
        inherited_perms = UserRepoToPerm.query()\
            .filter(UserRepoToPerm.repository_id == new_repo_id).all()
        self.assertEqual(len(inherited_perms), 2)

        self.assertTrue(TEST_USER_REGULAR_LOGIN in [x.user.username
                                                    for x in inherited_perms])
        self.assertTrue('repository.write' in [x.permission.permission_name
                                               for x in inherited_perms])

        RepoModel().delete(repo_name_full)
        RepoGroupModel().delete(group_name)
        Session().commit()

    def test_create_remote_repo_wrong_clone_uri(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                clone_uri='http://127.0.0.1/repo'))
        response.mustcontain('invalid clone url')


    def test_create_remote_repo_wrong_clone_uri_hg_svn(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description,
                                                clone_uri='svn+http://127.0.0.1/repo'))
        response.mustcontain('invalid clone url')


    def test_delete(self):
        self.log_user()
        repo_name = 'vcs_test_new_to_delete_%s' % self.REPO_TYPE
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_type=self.REPO_TYPE,
                                                repo_name=repo_name,
                                                repo_description=description))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name))
        self.checkSessionFlash(response,
                               'Created repository <a href="/%s">%s</a>'
                               % (repo_name, repo_name))
        # test if the repo was created in the database
        new_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name).one()

        self.assertEqual(new_repo.repo_name, repo_name)
        self.assertEqual(new_repo.description, description)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name))
        response.mustcontain(repo_name)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(os.path.join(TESTS_TMP_PATH, repo_name))
        except Exception:
            self.fail('no repo %s in filesystem' % repo_name)

        response = self.app.delete(url('repo', repo_name=repo_name))

        self.checkSessionFlash(response, 'Deleted repository %s' % (repo_name))

        response.follow()

        #check if repo was deleted from db
        deleted_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name).scalar()

        self.assertEqual(deleted_repo, None)

        self.assertEqual(os.path.isdir(os.path.join(TESTS_TMP_PATH, repo_name)),
                                  False)

    def test_delete_non_ascii(self):
        self.log_user()
        non_ascii = "ąęł"
        repo_name = "%s%s" % (self.NEW_REPO, non_ascii)
        repo_name_unicode = repo_name.decode('utf8')
        description = 'description for newly created repo' + non_ascii
        description_unicode = description.decode('utf8')
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description))
        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=repo_name))
        self.assertEqual(response.json, {u'result': True})
        self.checkSessionFlash(response,
                               u'Created repository <a href="/%s">%s</a>'
                               % (urllib.quote(repo_name), repo_name_unicode))
        # test if the repo was created in the database
        new_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name_unicode).one()

        self.assertEqual(new_repo.repo_name, repo_name_unicode)
        self.assertEqual(new_repo.description, description_unicode)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=repo_name))
        response.mustcontain(repo_name)
        response.mustcontain(self.REPO_TYPE)

        # test if the repository was created on filesystem
        try:
            vcs.get_repo(os.path.join(TESTS_TMP_PATH, repo_name))
        except Exception:
            self.fail('no repo %s in filesystem' % repo_name)

        response = self.app.delete(url('repo', repo_name=repo_name))
        self.checkSessionFlash(response, 'Deleted repository %s' % (repo_name_unicode))
        response.follow()

        #check if repo was deleted from db
        deleted_repo = Session().query(Repository)\
            .filter(Repository.repo_name == repo_name_unicode).scalar()

        self.assertEqual(deleted_repo, None)

        self.assertEqual(os.path.isdir(os.path.join(TESTS_TMP_PATH, repo_name)),
                                  False)

    def test_delete_repo_with_group(self):
        #TODO:
        pass

    def test_delete_browser_fakeout(self):
        response = self.app.post(url('repo', repo_name=self.REPO),
                                 params=dict(_method='delete'))

    def test_show(self):
        self.log_user()
        response = self.app.get(url('repo', repo_name=self.REPO))

    def test_edit(self):
        response = self.app.get(url('edit_repo', repo_name=self.REPO))

    def test_set_private_flag_sets_default_to_none(self):
        self.log_user()
        #initially repository perm should be read
        perm = _get_permission_for_user(user='default', repo=self.REPO)
        self.assertTrue(len(perm), 1)
        self.assertEqual(perm[0].permission.permission_name, 'repository.read')
        self.assertEqual(Repository.get_by_repo_name(self.REPO).private, False)

        response = self.app.put(url('repo', repo_name=self.REPO),
                        fixture._get_repo_create_params(repo_private=1,
                                                repo_name=self.REPO,
                                                repo_type=self.REPO_TYPE,
                                                user=TEST_USER_ADMIN_LOGIN))
        self.checkSessionFlash(response,
                               msg='Repository %s updated successfully' % (self.REPO))
        self.assertEqual(Repository.get_by_repo_name(self.REPO).private, True)

        #now the repo default permission should be None
        perm = _get_permission_for_user(user='default', repo=self.REPO)
        self.assertTrue(len(perm), 1)
        self.assertEqual(perm[0].permission.permission_name, 'repository.none')

        response = self.app.put(url('repo', repo_name=self.REPO),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=self.REPO,
                                                repo_type=self.REPO_TYPE,
                                                user=TEST_USER_ADMIN_LOGIN))
        self.checkSessionFlash(response,
                               msg='Repository %s updated successfully' % (self.REPO))
        self.assertEqual(Repository.get_by_repo_name(self.REPO).private, False)

        #we turn off private now the repo default permission should stay None
        perm = _get_permission_for_user(user='default', repo=self.REPO)
        self.assertTrue(len(perm), 1)
        self.assertEqual(perm[0].permission.permission_name, 'repository.none')

        #update this permission back
        perm[0].permission = Permission.get_by_key('repository.read')
        Session().add(perm[0])
        Session().commit()

    def test_set_repo_fork_has_no_self_id(self):
        self.log_user()
        repo = Repository.get_by_repo_name(self.REPO)
        response = self.app.get(url('edit_repo_advanced', repo_name=self.REPO))
        opt = """<option value="%s">vcs_test_git</option>""" % repo.repo_id
        response.mustcontain(no=[opt])

    def test_set_fork_of_other_repo(self):
        self.log_user()
        other_repo = 'other_%s' % self.REPO_TYPE
        fixture.create_repo(other_repo, repo_type=self.REPO_TYPE)
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(other_repo)
        response = self.app.put(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=repo2.repo_id))
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(other_repo)
        self.checkSessionFlash(response,
            'Marked repo %s as fork of %s' % (repo.repo_name, repo2.repo_name))

        assert repo.fork == repo2
        response = response.follow()
        # check if given repo is selected

        opt = """<option value="%s" selected="selected">%s</option>""" % (
                    repo2.repo_id, repo2.repo_name)
        response.mustcontain(opt)

        fixture.destroy_repo(other_repo, forks='detach')

    def test_set_fork_of_other_type_repo(self):
        self.log_user()
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(self.OTHER_TYPE_REPO)
        response = self.app.put(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=repo2.repo_id))
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(self.OTHER_TYPE_REPO)
        self.checkSessionFlash(response,
            'Cannot set repository as fork of repository with other type')

    def test_set_fork_of_none(self):
        self.log_user()
        ## mark it as None
        response = self.app.put(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=None))
        repo = Repository.get_by_repo_name(self.REPO)
        repo2 = Repository.get_by_repo_name(self.OTHER_TYPE_REPO)
        self.checkSessionFlash(response,
                               'Marked repo %s as fork of %s'
                               % (repo.repo_name, "Nothing"))
        assert repo.fork is None

    def test_set_fork_of_same_repo(self):
        self.log_user()
        repo = Repository.get_by_repo_name(self.REPO)
        response = self.app.put(url('edit_repo_advanced_fork', repo_name=self.REPO),
                                params=dict(id_fork_of=repo.repo_id))
        self.checkSessionFlash(response,
                               'An error occurred during this operation')

    def test_create_on_top_level_without_permissions(self):
        usr = self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        # revoke
        user_model = UserModel()
        # disable fork and create on default user
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.create.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.create.none')
        user_model.revoke_perm(User.DEFAULT_USER, 'hg.fork.repository')
        user_model.grant_perm(User.DEFAULT_USER, 'hg.fork.none')

        # disable on regular user
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.create.none')
        user_model.revoke_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.repository')
        user_model.grant_perm(TEST_USER_REGULAR_LOGIN, 'hg.fork.none')
        Session().commit()


        user = User.get(usr['user_id'])

        repo_name = self.NEW_REPO+'no_perms'
        description = 'description for newly created repo'
        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description))

        response.mustcontain('no permission to create repository in root location')

        RepoModel().delete(repo_name)
        Session().commit()

    @mock.patch.object(RepoModel, '_create_filesystem_repo', error_function)
    def test_create_repo_when_filesystem_op_fails(self):
        self.log_user()
        repo_name = self.NEW_REPO
        description = 'description for newly created repo'

        response = self.app.post(url('repos'),
                        fixture._get_repo_create_params(repo_private=False,
                                                repo_name=repo_name,
                                                repo_type=self.REPO_TYPE,
                                                repo_description=description))

        self.checkSessionFlash(response,
                               'Error creating repository %s' % repo_name)
        # repo must not be in db
        repo = Repository.get_by_repo_name(repo_name)
        self.assertEqual(repo, None)

        # repo must not be in filesystem !
        self.assertFalse(os.path.isdir(os.path.join(TESTS_TMP_PATH, repo_name)))

class TestAdminReposControllerGIT(_BaseTest):
    REPO = GIT_REPO
    REPO_TYPE = 'git'
    NEW_REPO = NEW_GIT_REPO
    OTHER_TYPE_REPO = HG_REPO
    OTHER_TYPE = 'hg'


class TestAdminReposControllerHG(_BaseTest):
    REPO = HG_REPO
    REPO_TYPE = 'hg'
    NEW_REPO = NEW_HG_REPO
    OTHER_TYPE_REPO = GIT_REPO
    OTHER_TYPE = 'git'
