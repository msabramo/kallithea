# -*- coding: utf-8 -*-

from kallithea.model.db import User, UserFollowing, Repository, UserApiKeys
from kallithea.tests import *
from kallithea.tests.fixture import Fixture
from kallithea.lib import helpers as h
from kallithea.model.user import UserModel
from kallithea.model.meta import Session

fixture = Fixture()


class TestMyAccountController(TestController):
    test_user_1 = 'testme'

    @classmethod
    def teardown_class(cls):
        if User.get_by_username(cls.test_user_1):
            UserModel().delete(cls.test_user_1)
            Session().commit()

    def test_my_account(self):
        self.log_user()
        response = self.app.get(url('my_account'))

        response.mustcontain('value="test_admin')

    def test_my_account_my_repos(self):
        self.log_user()
        response = self.app.get(url('my_account_repos'))
        cnt = Repository.query().filter(Repository.user ==
                           User.get_by_username(TEST_USER_ADMIN_LOGIN)).count()
        response.mustcontain('"totalRecords": %s' % cnt)

    def test_my_account_my_watched(self):
        self.log_user()
        response = self.app.get(url('my_account_watched'))

        cnt = UserFollowing.query().filter(UserFollowing.user ==
                            User.get_by_username(TEST_USER_ADMIN_LOGIN)).count()
        response.mustcontain('"totalRecords": %s' % cnt)

    def test_my_account_my_emails(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')

    def test_my_account_my_emails_add_existing_email(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')
        response = self.app.post(url('my_account_emails'),
                                 {'new_email': TEST_USER_REGULAR_EMAIL})
        self.checkSessionFlash(response, 'This e-mail address is already taken')

    def test_my_account_my_emails_add_mising_email_in_form(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')
        response = self.app.post(url('my_account_emails'),)
        self.checkSessionFlash(response, 'Please enter an email address')

    def test_my_account_my_emails_add_remove(self):
        self.log_user()
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')

        response = self.app.post(url('my_account_emails'),
                                 {'new_email': 'foo@barz.com'})

        response = self.app.get(url('my_account_emails'))

        from kallithea.model.db import UserEmailMap
        email_id = UserEmailMap.query()\
            .filter(UserEmailMap.user == User.get_by_username(TEST_USER_ADMIN_LOGIN))\
            .filter(UserEmailMap.email == 'foo@barz.com').one().email_id

        response.mustcontain('foo@barz.com')
        response.mustcontain('<input id="del_email_id" name="del_email_id" type="hidden" value="%s" />' % email_id)

        response = self.app.post(url('my_account_emails'),
                                 {'del_email_id': email_id, '_method': 'delete'})
        self.checkSessionFlash(response, 'Removed email from user')
        response = self.app.get(url('my_account_emails'))
        response.mustcontain('No additional emails specified')


    @parameterized.expand(
        [('firstname', {'firstname': 'new_username'}),
         ('lastname', {'lastname': 'new_username'}),
         ('admin', {'admin': True}),
         ('admin', {'admin': False}),
         ('extern_type', {'extern_type': 'ldap'}),
         ('extern_type', {'extern_type': None}),
         #('extern_name', {'extern_name': 'test'}),
         #('extern_name', {'extern_name': None}),
         ('active', {'active': False}),
         ('active', {'active': True}),
         ('email', {'email': 'some@email.com'}),
        # ('new_password', {'new_password': 'foobar123',
        #                   'password_confirmation': 'foobar123'})
        ])
    def test_my_account_update(self, name, attrs):
        usr = fixture.create_user(self.test_user_1, password='qweqwe',
                                  email='testme@example.com',
                                  extern_type='internal',
                                  extern_name=self.test_user_1,
                                  skip_if_exists=True)
        params = usr.get_api_data()  # current user data
        user_id = usr.user_id
        self.log_user(username=self.test_user_1, password='qweqwe')

        params.update({'password_confirmation': ''})
        params.update({'new_password': ''})
        params.update({'extern_type': 'internal'})
        params.update({'extern_name': self.test_user_1})

        params.update(attrs)
        response = self.app.post(url('my_account'), params)

        self.checkSessionFlash(response,
                               'Your account was updated successfully')

        updated_user = User.get_by_username(self.test_user_1)
        updated_params = updated_user.get_api_data()
        updated_params.update({'password_confirmation': ''})
        updated_params.update({'new_password': ''})

        params['last_login'] = updated_params['last_login']
        if name == 'email':
            params['emails'] = [attrs['email']]
        if name == 'extern_type':
            #cannot update this via form, expected value is original one
            params['extern_type'] = "internal"
        if name == 'extern_name':
            #cannot update this via form, expected value is original one
            params['extern_name'] = str(user_id)
        if name == 'active':
            #my account cannot deactivate account
            params['active'] = True
        if name == 'admin':
            #my account cannot make you an admin !
            params['admin'] = False

        self.assertEqual(params, updated_params)

    def test_my_account_update_err_email_exists(self):
        self.log_user()

        new_email = 'test_regular@mail.com'  # already exisitn email
        response = self.app.post(url('my_account'),
                                params=dict(
                                    username='test_admin',
                                    new_password='test12',
                                    password_confirmation='test122',
                                    firstname='NewName',
                                    lastname='NewLastname',
                                    email=new_email,)
                                )

        response.mustcontain('This e-mail address is already taken')

    def test_my_account_update_err(self):
        self.log_user('test_regular2', 'test12')

        new_email = 'newmail.pl'
        response = self.app.post(url('my_account'),
                                 params=dict(
                                            username='test_admin',
                                            new_password='test12',
                                            password_confirmation='test122',
                                            firstname='NewName',
                                            lastname='NewLastname',
                                            email=new_email,))

        response.mustcontain('An email address must contain a single @')
        from kallithea.model import validators
        msg = validators.ValidUsername(edit=False, old_data={})\
                ._messages['username_exists']
        msg = h.html_escape(msg % {'username': 'test_admin'})
        response.mustcontain(u"%s" % msg)

    def test_my_account_api_keys(self):
        usr = self.log_user('test_regular2', 'test12')
        user = User.get(usr['user_id'])
        response = self.app.get(url('my_account_api_keys'))
        response.mustcontain(user.api_key)
        response.mustcontain('expires: never')

    @parameterized.expand([
        ('forever', -1),
        ('5mins', 60*5),
        ('30days', 60*60*24*30),
    ])
    def test_my_account_add_api_keys(self, desc, lifetime):
        usr = self.log_user('test_regular2', 'test12')
        user = User.get(usr['user_id'])
        response = self.app.post(url('my_account_api_keys'),
                                 {'description': desc, 'lifetime': lifetime})
        self.checkSessionFlash(response, 'Api key successfully created')
        try:
            response = response.follow()
            user = User.get(usr['user_id'])
            for api_key in user.api_keys:
                response.mustcontain(api_key)
        finally:
            for api_key in UserApiKeys.query().all():
                Session().delete(api_key)
                Session().commit()

    def test_my_account_remove_api_key(self):
        usr = self.log_user('test_regular2', 'test12')
        user = User.get(usr['user_id'])
        response = self.app.post(url('my_account_api_keys'),
                                 {'description': 'desc', 'lifetime': -1})
        self.checkSessionFlash(response, 'Api key successfully created')
        response = response.follow()

        #now delete our key
        keys = UserApiKeys.query().all()
        self.assertEqual(1, len(keys))

        response = self.app.post(url('my_account_api_keys'),
                 {'_method': 'delete', 'del_api_key': keys[0].api_key})
        self.checkSessionFlash(response, 'Api key successfully deleted')
        keys = UserApiKeys.query().all()
        self.assertEqual(0, len(keys))


    def test_my_account_reset_main_api_key(self):
        usr = self.log_user('test_regular2', 'test12')
        user = User.get(usr['user_id'])
        api_key = user.api_key
        response = self.app.get(url('my_account_api_keys'))
        response.mustcontain(api_key)
        response.mustcontain('expires: never')

        response = self.app.post(url('my_account_api_keys'),
                 {'_method': 'delete', 'del_api_key_builtin': api_key})
        self.checkSessionFlash(response, 'Api key successfully reset')
        response = response.follow()
        response.mustcontain(no=[api_key])
