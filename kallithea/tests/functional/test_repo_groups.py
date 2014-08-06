from kallithea.tests import *


class TestRepoGroupsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url('repos_groups'))
        response.mustcontain('{"totalRecords": 0, "sort": null, "startIndex": 0, "dir": "asc", "records": []};')

#    def test_create(self):
#        response = self.app.post(url('repos_groups'))

    def test_new(self):
        self.log_user()
        response = self.app.get(url('new_repos_group'))

    def test_new_by_regular_user(self):
        self.log_user(TEST_USER_REGULAR_LOGIN, TEST_USER_REGULAR_PASS)
        response = self.app.get(url('new_repos_group'), status=403)
#
#    def test_update(self):
#        response = self.app.put(url('repos_group', group_name=1))
#
#    def test_delete(self):
#        self.log_user()
#        response = self.app.delete(url('repos_group', group_name=1))
#
#    def test_show(self):
#        response = self.app.get(url('repos_group', group_name=1))
#
#    def test_edit(self):
#        response = self.app.get(url('edit_repo_group', group_name=1))
