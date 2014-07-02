from kallithea.model.db import User, UserIpMap
from kallithea.tests import *

class TestAdminPermissionsController(TestController):

    def test_index(self):
        self.log_user()
        response = self.app.get(url('admin_permissions'))
        # Test response...

    def test_index_ips(self):
        self.log_user()
        response = self.app.get(url('admin_permissions_ips'))
        # Test response...
        response.mustcontain('All IP addresses are allowed')

    def test_add_ips(self):
        self.log_user()
        default_user_id = User.get_default_user().user_id
        response = self.app.put(url('edit_user_ips', id=default_user_id),
                                 params=dict(new_ip='127.0.0.0/24'))

        response = self.app.get(url('admin_permissions_ips'))
        response.mustcontain('127.0.0.0/24')
        response.mustcontain('127.0.0.0 - 127.0.0.255')

        ## delete
        default_user_id = User.get_default_user().user_id
        del_ip_id = UserIpMap.query().filter(UserIpMap.user_id ==
                                             default_user_id).first().ip_id

        response = self.app.post(url('edit_user_ips', id=default_user_id),
                                 params=dict(_method='delete',
                                             del_ip_id=del_ip_id))

        response = self.app.get(url('admin_permissions_ips'))
        response.mustcontain('All IP addresses are allowed')
        response.mustcontain(no=['127.0.0.0/24'])
        response.mustcontain(no=['127.0.0.0 - 127.0.0.255'])


    def test_index_overview(self):
        self.log_user()
        response = self.app.get(url('admin_permissions_perms'))
        # Test response...
