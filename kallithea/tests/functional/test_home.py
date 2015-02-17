from kallithea.tests import *
from kallithea.tests.fixture import Fixture
from kallithea.model.meta import Session
from kallithea.model.db import Repository
from kallithea.model.repo import RepoModel
from kallithea.model.repo_group import RepoGroupModel


fixture = Fixture()


class TestHomeController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url(controller='home', action='index'))
        #if global permission is set
        response.mustcontain('Add Repository')
        # html in javascript variable:
        response.mustcontain('var data = {"totalRecords": %s' % len(Repository.getAll()))
        response.mustcontain(r'href=\"/%s\"' % HG_REPO)

        response.mustcontain(r'<span class="repotag">git')
        response.mustcontain(r'<i class=\"icon-globe\"')

        response.mustcontain("""fixes issue with having custom format for git-log""")
        response.mustcontain("""/%s/changeset/5f2c6ee195929b0be80749243c18121c9864a3b3""" % GIT_REPO)

        response.mustcontain("""disable security checks on hg clone for travis""")
        response.mustcontain("""/%s/changeset/96507bd11ecc815ebc6270fdf6db110928c09c1e""" % HG_REPO)

    def test_repo_summary_with_anonymous_access_disabled(self):
        with fixture.anon_access(False):
            response = self.app.get(url(controller='summary',
                                        action='index', repo_name=HG_REPO),
                                        status=302)
            assert 'login' in response.location

    def test_index_with_anonymous_access_disabled(self):
        with fixture.anon_access(False):
            response = self.app.get(url(controller='home', action='index'),
                                    status=302)
            assert 'login' in response.location

    def test_index_page_on_groups(self):
        self.log_user()
        gr = fixture.create_repo_group('gr1')
        fixture.create_repo(name='gr1/repo_in_group', repo_group=gr)
        response = self.app.get(url('repos_group_home', group_name='gr1'))

        try:
            response.mustcontain("gr1/repo_in_group")
        finally:
            RepoModel().delete('gr1/repo_in_group')
            RepoGroupModel().delete(repo_group='gr1', force_delete=True)
            Session().commit()
