# -*- coding: utf-8 -*-

from kallithea.model.db import Setting, Ui
from kallithea.tests import *
from kallithea.tests.fixture import Fixture

fixture = Fixture()


class TestAdminSettingsController(TestController):

    def test_index_main(self):
        self.log_user()
        response = self.app.get(url('admin_settings'))

    def test_index_mapping(self):
        self.log_user()
        response = self.app.get(url('admin_settings_mapping'))

    def test_index_global(self):
        self.log_user()
        response = self.app.get(url('admin_settings_global'))

    def test_index_visual(self):
        self.log_user()
        response = self.app.get(url('admin_settings_visual'))

    def test_index_email(self):
        self.log_user()
        response = self.app.get(url('admin_settings_email'))

    def test_index_hooks(self):
        self.log_user()
        response = self.app.get(url('admin_settings_hooks'))

    def test_create_custom_hook(self):
        self.log_user()
        response = self.app.post(url('admin_settings_hooks'),
                                params=dict(new_hook_ui_key='test_hooks_1',
                                            new_hook_ui_value='cd /tmp'))

        response = response.follow()
        response.mustcontain('test_hooks_1')
        response.mustcontain('cd /tmp')

    def test_create_custom_hook_delete(self):
        self.log_user()
        response = self.app.post(url('admin_settings_hooks'),
                                params=dict(new_hook_ui_key='test_hooks_2',
                                            new_hook_ui_value='cd /tmp2'))

        response = response.follow()
        response.mustcontain('test_hooks_2')
        response.mustcontain('cd /tmp2')

        hook_id = Ui.get_by_key('test_hooks_2').ui_id
        ## delete
        self.app.post(url('admin_settings_hooks'),
                        params=dict(hook_id=hook_id))
        response = self.app.get(url('admin_settings_hooks'))
        response.mustcontain(no=['test_hooks_2'])
        response.mustcontain(no=['cd /tmp2'])

    def test_index_search(self):
        self.log_user()
        response = self.app.get(url('admin_settings_search'))

    def test_index_system(self):
        self.log_user()
        response = self.app.get(url('admin_settings_system'))

    def test_ga_code_active(self):
        self.log_user()
        old_title = 'Kallithea'
        old_realm = 'Kallithea authentication'
        new_ga_code = 'ga-test-123456789'
        response = self.app.post(url('admin_settings_global'),
                        params=dict(title=old_title,
                                 realm=old_realm,
                                 ga_code=new_ga_code,
                                 captcha_private_key='',
                                 captcha_public_key='',
                                 ))

        self.checkSessionFlash(response, 'Updated application settings')

        self.assertEqual(Setting
                         .get_app_settings()['ga_code'], new_ga_code)

        response = response.follow()
        response.mustcontain("""_gaq.push(['_setAccount', '%s']);""" % new_ga_code)

    def test_ga_code_inactive(self):
        self.log_user()
        old_title = 'Kallithea'
        old_realm = 'Kallithea authentication'
        new_ga_code = ''
        response = self.app.post(url('admin_settings_global'),
                        params=dict(title=old_title,
                                 realm=old_realm,
                                 ga_code=new_ga_code,
                                 captcha_private_key='',
                                 captcha_public_key='',
                                 ))

        self.checkSessionFlash(response, 'Updated application settings')
        self.assertEqual(Setting
                        .get_app_settings()['ga_code'], new_ga_code)

        response = response.follow()
        response.mustcontain(no=["_gaq.push(['_setAccount', '%s']);" % new_ga_code])

    def test_captcha_activate(self):
        self.log_user()
        old_title = 'Kallithea'
        old_realm = 'Kallithea authentication'
        new_ga_code = ''
        response = self.app.post(url('admin_settings_global'),
                        params=dict(title=old_title,
                                 realm=old_realm,
                                 ga_code=new_ga_code,
                                 captcha_private_key='1234567890',
                                 captcha_public_key='1234567890',
                                 ))

        self.checkSessionFlash(response, 'Updated application settings')
        self.assertEqual(Setting
                        .get_app_settings()['captcha_private_key'], '1234567890')

        response = self.app.get(url('register'))
        response.mustcontain('captcha')

    def test_captcha_deactivate(self):
        self.log_user()
        old_title = 'Kallithea'
        old_realm = 'Kallithea authentication'
        new_ga_code = ''
        response = self.app.post(url('admin_settings_global'),
                        params=dict(title=old_title,
                                 realm=old_realm,
                                 ga_code=new_ga_code,
                                 captcha_private_key='',
                                 captcha_public_key='1234567890',
                                 ))

        self.checkSessionFlash(response, 'Updated application settings')
        self.assertEqual(Setting
                        .get_app_settings()['captcha_private_key'], '')

        response = self.app.get(url('register'))
        response.mustcontain(no=['captcha'])

    def test_title_change(self):
        self.log_user()
        old_title = 'Kallithea'
        new_title = old_title + '_changed'
        old_realm = 'Kallithea authentication'

        for new_title in ['Changed', 'Żółwik', old_title]:
            response = self.app.post(url('admin_settings_global'),
                        params=dict(title=new_title,
                                 realm=old_realm,
                                 ga_code='',
                                 captcha_private_key='',
                                 captcha_public_key='',
                                ))

            self.checkSessionFlash(response, 'Updated application settings')
            self.assertEqual(Setting
                             .get_app_settings()['title'],
                             new_title.decode('utf-8'))

            response = response.follow()
            response.mustcontain("""<div class="branding">%s</div>""" % new_title)
