from kallithea.tests import *

class TestChangesetController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='changeset', action='index',
                                    repo_name=HG_REPO, revision='tip'))
        # Test response...

    def test_changeset_range(self):
        #print self.app.get(url(controller='changelog', action='index', repo_name=HG_REPO))

        response = self.app.get(url(controller='changeset', action='index',
                                    repo_name=HG_REPO, revision='a53d9201d4bc278910d416d94941b7ea007ecd52...96507bd11ecc815ebc6270fdf6db110928c09c1e'))

        response = self.app.get(url(controller='changeset', action='changeset_raw',
                                    repo_name=HG_REPO, revision='a53d9201d4bc278910d416d94941b7ea007ecd52'))

        response = self.app.get(url(controller='changeset', action='changeset_patch',
                                    repo_name=HG_REPO, revision='a53d9201d4bc278910d416d94941b7ea007ecd52'))

        response = self.app.get(url(controller='changeset', action='changeset_download',
                                    repo_name=HG_REPO, revision='a53d9201d4bc278910d416d94941b7ea007ecd52'))
