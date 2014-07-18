from kallithea.tests import *


class TestBranchesController(TestController):

    def test_index_hg(self):
        self.log_user()
        response = self.app.get(url(controller='branches',
                                    action='index', repo_name=HG_REPO))
        response.mustcontain("""<a href="/%s/changelog?branch=default">default</a>""" % HG_REPO)

        # closed branches
        response.mustcontain("""<a href="/%s/changelog?branch=git">git [closed]</a>""" % HG_REPO)
        response.mustcontain("""<a href="/%s/changelog?branch=web">web [closed]</a>""" % HG_REPO)

    def test_index_git(self):
        self.log_user()
        response = self.app.get(url(controller='branches',
                                    action='index', repo_name=GIT_REPO))
        response.mustcontain("""<a href="/%s/changelog?branch=master">master</a>""" % GIT_REPO)
