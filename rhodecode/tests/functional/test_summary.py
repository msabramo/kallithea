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

from kallithea.tests import *
from kallithea.tests.fixture import Fixture
from kallithea.model.db import Repository
from kallithea.model.repo import RepoModel
from kallithea.model.meta import Session
from kallithea.model.scm import ScmModel

fixture = Fixture()


class TestSummaryController(TestController):

    def test_index(self):
        self.log_user()
        ID = Repository.get_by_repo_name(HG_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name=HG_REPO))

        #repo type
        response.mustcontain(
            """<i class="icon-hg" """
        )
        #public/private
        response.mustcontain(
            """<i class="icon-unlock-alt">"""
        )

        # clone url...
        response.mustcontain('''id="clone_url" readonly="readonly" value="http://test_admin@localhost:80/%s"''' % HG_REPO)
        response.mustcontain('''id="clone_url_id" readonly="readonly" value="http://test_admin@localhost:80/_%s"''' % ID)

    def test_index_git(self):
        self.log_user()
        ID = Repository.get_by_repo_name(GIT_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name=GIT_REPO))

        #repo type
        response.mustcontain(
            """<i class="icon-git" """
        )
        #public/private
        response.mustcontain(
            """<i class="icon-unlock-alt">"""
        )

        # clone url...
        response.mustcontain('''id="clone_url" readonly="readonly" value="http://test_admin@localhost:80/%s"''' % GIT_REPO)
        response.mustcontain('''id="clone_url_id" readonly="readonly" value="http://test_admin@localhost:80/_%s"''' % ID)

    def test_index_by_id_hg(self):
        self.log_user()
        ID = Repository.get_by_repo_name(HG_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name='_%s' % ID))

        #repo type
        response.mustcontain(
            """<i class="icon-hg" """
        )
        #public/private
        response.mustcontain(
            """<i class="icon-unlock-alt">"""
        )

    def test_index_by_repo_having_id_path_in_name_hg(self):
        self.log_user()
        fixture.create_repo(name='repo_1')
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name='repo_1'))

        try:
            response.mustcontain("repo_1")
        finally:
            RepoModel().delete(Repository.get_by_repo_name('repo_1'))
            Session().commit()

    def test_index_by_id_git(self):
        self.log_user()
        ID = Repository.get_by_repo_name(GIT_REPO).repo_id
        response = self.app.get(url(controller='summary',
                                    action='index',
                                    repo_name='_%s' % ID))

        #repo type
        response.mustcontain(
            """<i class="icon-git" """
        )
        #public/private
        response.mustcontain(
            """<i class="icon-unlock-alt">"""
        )

    def _enable_stats(self, repo):
        r = Repository.get_by_repo_name(repo)
        r.enable_statistics = True
        Session().add(r)
        Session().commit()

    def test_index_trending(self):
        self.log_user()
        #codes stats
        self._enable_stats(HG_REPO)

        ScmModel().mark_for_invalidation(HG_REPO)
        response = self.app.get(url(controller='summary', action='index',
                                    repo_name=HG_REPO))
        response.mustcontain(
            '[["py", {"count": 68, "desc": ["Python"]}], '
            '["rst", {"count": 16, "desc": ["Rst"]}], '
            '["css", {"count": 2, "desc": ["Css"]}], '
            '["sh", {"count": 2, "desc": ["Bash"]}], '
            '["yml", {"count": 1, "desc": ["Yaml"]}], '
            '["makefile", {"count": 1, "desc": ["Makefile", "Makefile"]}], '
            '["js", {"count": 1, "desc": ["Javascript"]}], '
            '["cfg", {"count": 1, "desc": ["Ini"]}], '
            '["ini", {"count": 1, "desc": ["Ini"]}], '
            '["html", {"count": 1, "desc": ["EvoqueHtml", "Html"]}]];'
        )

    def test_index_statistics(self):
        self.log_user()
        #codes stats
        self._enable_stats(HG_REPO)

        ScmModel().mark_for_invalidation(HG_REPO)
        response = self.app.get(url(controller='summary', action='statistics',
                                    repo_name=HG_REPO))

    def test_index_trending_git(self):
        self.log_user()
        #codes stats
        self._enable_stats(GIT_REPO)

        ScmModel().mark_for_invalidation(GIT_REPO)
        response = self.app.get(url(controller='summary', action='index',
                                    repo_name=GIT_REPO))
        response.mustcontain(
            '[["py", {"count": 68, "desc": ["Python"]}], '
            '["rst", {"count": 16, "desc": ["Rst"]}], '
            '["css", {"count": 2, "desc": ["Css"]}], '
            '["sh", {"count": 2, "desc": ["Bash"]}], '
            '["makefile", {"count": 1, "desc": ["Makefile", "Makefile"]}], '
            '["js", {"count": 1, "desc": ["Javascript"]}], '
            '["cfg", {"count": 1, "desc": ["Ini"]}], '
            '["ini", {"count": 1, "desc": ["Ini"]}], '
            '["html", {"count": 1, "desc": ["EvoqueHtml", "Html"]}], '
            '["bat", {"count": 1, "desc": ["Batch"]}]];'
        )

    def test_index_statistics_git(self):
        self.log_user()
        #codes stats
        self._enable_stats(GIT_REPO)

        ScmModel().mark_for_invalidation(GIT_REPO)
        response = self.app.get(url(controller='summary', action='statistics',
                                    repo_name=GIT_REPO))
