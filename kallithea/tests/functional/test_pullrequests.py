from kallithea.tests import *
from kallithea.tests.fixture import Fixture
from kallithea.model.meta import Session

from kallithea.controllers.pullrequests import PullrequestsController

fixture = Fixture()

class TestPullrequestsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url(controller='pullrequests', action='index',
                                    repo_name=HG_REPO))

class TestPullrequestsGetRepoRefs(TestController):

    def setUp(self):
        self.main = fixture.create_repo('main', repo_type='hg')
        Session.add(self.main)
        Session.commit()
        self.c = PullrequestsController()

    def tearDown(self):
        fixture.destroy_repo('main')
        Session.commit()
        Session.remove()

    def test_repo_refs_empty_repo(self):
        # empty repo with no commits, no branches, no bookmarks, just one tag
        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        self.assertEqual(default, 'tag:null:0000000000000000000000000000000000000000')

    def test_repo_refs_one_commit_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        self.assertEqual(default, 'branch:default:%s' % cs0.raw_id)
        self.assertIn(([('branch:default:%s' % cs0.raw_id, 'default (current tip)')],
                'Branches'), refs)

    def test_repo_refs_one_commit_rev_hint(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs0.raw_id)
        expected = 'branch:default:%s' % cs0.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_two_commits_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance)
        expected = 'branch:default:%s' % cs1.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_two_commits_rev_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs0.raw_id)
        expected = 'rev:%s:%s' % (cs0.raw_id, cs0.raw_id)
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'Changeset: %s' % cs0.raw_id[0:12])], 'Special'), refs)
        self.assertIn(([('branch:default:%s' % cs1.raw_id, 'default (current tip)')], 'Branches'), refs)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, rev=cs1.raw_id)
        expected = 'branch:default:%s' % cs1.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_two_commits_branch_hint(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        cs1 = fixture.commit_change(self.main.repo_name, filename='file2',
                content='line2\n', message='commit2', vcs_type='hg',
                parent=None, newfile=True)

        refs, default = self.c._get_repo_refs(self.main.scm_instance, branch='default')
        expected = 'branch:default:%s' % cs1.raw_id
        self.assertEqual(default, expected)
        self.assertIn(([(expected, 'default (current tip)')], 'Branches'), refs)

    def test_repo_refs_one_branch_no_hints(self):
        cs0 = fixture.commit_change(self.main.repo_name, filename='file1',
                content='line1\n', message='commit1', vcs_type='hg',
                parent=None, newfile=True)
        # TODO
