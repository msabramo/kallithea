# -*- coding: utf-8 -*-
from kallithea.tests import *
from kallithea.tests.fixture import Fixture

from kallithea.model.db import Repository
from kallithea.model.repo import RepoModel
from kallithea.model.user import UserModel
from kallithea.model.meta import Session

fixture = Fixture()

from kallithea.tests import *


class _BaseTest(TestController):
    """
    Write all tests here
    """
    REPO = None
    REPO_TYPE = None
    NEW_REPO = None
    REPO_FORK = None

    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def setUp(self):
        self.username = u'forkuser'
        self.password = u'qweqwe'
        self.u1 = fixture.create_user(self.username, password=self.password,
                                      email=u'fork_king@example.com')
        Session().commit()

    def tearDown(self):
        Session().delete(self.u1)
        Session().commit()

    def test_index(self):
        self.log_user()
        repo_name = self.REPO
        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain("""There are no forks yet""")

    def test_no_permissions_to_fork(self):
        usr = self.log_user(TEST_USER_REGULAR_LOGIN,
                            TEST_USER_REGULAR_PASS)['user_id']
        user_model = UserModel()
        user_model.revoke_perm(usr, 'hg.fork.repository')
        user_model.grant_perm(usr, 'hg.fork.none')
        u = UserModel().get(usr)
        u.inherit_default_permissions = False
        Session().commit()
        # try create a fork
        repo_name = self.REPO
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), {}, status=403)

    def test_index_with_fork(self):
        self.log_user()

        # create a fork
        fork_name = self.REPO_FORK
        description = 'fork of vcs test'
        repo_name = self.REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        creation_args = {
            'repo_name': fork_name,
            'repo_group': '',
            'fork_parent_id': org_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': description,
            'private': 'False',
            'landing_rev': 'rev:tip'}

        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), creation_args)

        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain(
            """<a href="/%s">%s</a>""" % (fork_name, fork_name)
        )

        # remove this fork
        response = self.app.delete(url('repo', repo_name=fork_name))

    def test_fork_create_into_group(self):
        self.log_user()
        group = fixture.create_repo_group('vc')
        group_id = group.group_id
        fork_name = self.REPO_FORK
        fork_name_full = 'vc/%s' % fork_name
        description = 'fork of vcs test'
        repo_name = self.REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        creation_args = {
            'repo_name': fork_name,
            'repo_group': group_id,
            'fork_parent_id': org_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': description,
            'private': 'False',
            'landing_rev': 'rev:tip'}
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), creation_args)
        repo = Repository.get_by_repo_name(fork_name_full)
        assert repo.fork.repo_name == self.REPO

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=fork_name_full))
        #test if we have a message that fork is ok
        self.checkSessionFlash(response,
                'Forked repository %s as <a href="/%s">%s</a>'
                % (repo_name, fork_name_full, fork_name_full))

        #test if the fork was created in the database
        fork_repo = Session().query(Repository)\
            .filter(Repository.repo_name == fork_name_full).one()

        self.assertEqual(fork_repo.repo_name, fork_name_full)
        self.assertEqual(fork_repo.fork.repo_name, repo_name)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=fork_name_full))
        response.mustcontain(fork_name_full)
        response.mustcontain(self.REPO_TYPE)
        response.mustcontain('Fork of "<a href="/%s">%s</a>"' % (repo_name, repo_name))

        fixture.destroy_repo(fork_name_full)
        fixture.destroy_repo_group(group_id)

    def test_z_fork_create(self):
        self.log_user()
        fork_name = self.REPO_FORK
        description = 'fork of vcs test'
        repo_name = self.REPO
        org_repo = Repository.get_by_repo_name(repo_name)
        creation_args = {
            'repo_name': fork_name,
            'repo_group': '',
            'fork_parent_id': org_repo.repo_id,
            'repo_type': self.REPO_TYPE,
            'description': description,
            'private': 'False',
            'landing_rev': 'rev:tip'}
        self.app.post(url(controller='forks', action='fork_create',
                          repo_name=repo_name), creation_args)
        repo = Repository.get_by_repo_name(self.REPO_FORK)
        assert repo.fork.repo_name == self.REPO

        ## run the check page that triggers the flash message
        response = self.app.get(url('repo_check_home', repo_name=fork_name))
        #test if we have a message that fork is ok
        self.checkSessionFlash(response,
                'Forked repository %s as <a href="/%s">%s</a>'
                % (repo_name, fork_name, fork_name))

        #test if the fork was created in the database
        fork_repo = Session().query(Repository)\
            .filter(Repository.repo_name == fork_name).one()

        self.assertEqual(fork_repo.repo_name, fork_name)
        self.assertEqual(fork_repo.fork.repo_name, repo_name)

        # test if the repository is visible in the list ?
        response = self.app.get(url('summary_home', repo_name=fork_name))
        response.mustcontain(fork_name)
        response.mustcontain(self.REPO_TYPE)
        response.mustcontain('Fork of "<a href="/%s">%s</a>"' % (repo_name, repo_name))

    def test_zz_fork_permission_page(self):
        usr = self.log_user(self.username, self.password)['user_id']
        repo_name = self.REPO

        forks = Repository.query()\
            .filter(Repository.repo_type == self.REPO_TYPE)\
            .filter(Repository.fork_id != None).all()
        self.assertEqual(1, len(forks))

        # set read permissions for this
        RepoModel().grant_user_permission(repo=forks[0],
                                          user=usr,
                                          perm='repository.read')
        Session().commit()

        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))

        response.mustcontain('<div style="padding:5px 3px 3px 42px;">fork of vcs test</div>')

    def test_zzz_fork_permission_page(self):
        usr = self.log_user(self.username, self.password)['user_id']
        repo_name = self.REPO

        forks = Repository.query()\
            .filter(Repository.repo_type == self.REPO_TYPE)\
            .filter(Repository.fork_id != None).all()
        self.assertEqual(1, len(forks))

        # set none
        RepoModel().grant_user_permission(repo=forks[0],
                                          user=usr, perm='repository.none')
        Session().commit()
        # fork shouldn't be there
        response = self.app.get(url(controller='forks', action='forks',
                                    repo_name=repo_name))
        response.mustcontain('There are no forks yet')


class TestGIT(_BaseTest):
    REPO = GIT_REPO
    NEW_REPO = NEW_GIT_REPO
    REPO_TYPE = 'git'
    REPO_FORK = GIT_FORK


class TestHG(_BaseTest):
    REPO = HG_REPO
    NEW_REPO = NEW_HG_REPO
    REPO_TYPE = 'hg'
    REPO_FORK = HG_FORK
