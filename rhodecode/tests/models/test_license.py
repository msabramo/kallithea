from __future__ import with_statement

from rhodecode.tests import *
from rhodecode.tests.fixture import Fixture
from rhodecode.lib.compat import json
from rhodecode.model.license import LicenseModel

fixture = Fixture()

TEST_KEY = ''


class LicenseTest(BaseTestCase):

    def setUp(self):
        global TEST_KEY
        token = LicenseModel.generate_license_token()
        TEST_KEY = token

    def test_encryption_decryption(self):
        test_license = {
            'foo': 'baar',
            'signature': 'test'
        }
        enc = LicenseModel(key=TEST_KEY).encrypt(json.dumps(test_license))
        dec = json.loads(LicenseModel(key=TEST_KEY).decrypt(enc))
        self.assertEqual(test_license, dec)

    def test_signature(self):
        enc_with_key = '1234567890123456'
        test_license = {
            'foo': 'baar',
            'signature': None
        }
        test_license['signature'] = LicenseModel(key=TEST_KEY)\
            .generate_signature(test_license, enc_with_key)

        enc = LicenseModel(key=TEST_KEY).encrypt(json.dumps(test_license))
        signature = LicenseModel(key=TEST_KEY).verify(enc, enc_with_key)

        del test_license['signature']
        self.assertEqual(test_license, signature)

    def test_signature_mismatch(self):
        enc_with_key = '1234567890123456'
        test_license = {
            'foo': 'baar',
            'signature': 'cnashs62tdsbcsaaisuda6215sagc'
        }

        enc = LicenseModel(key=TEST_KEY).encrypt(json.dumps(test_license))

        self.assertRaises(TypeError,
            lambda: LicenseModel(key=TEST_KEY).verify(enc, enc_with_key))

    def test_generate_license_token(self):
        token = LicenseModel.generate_license_token()
        self.assertEqual(4, len(token.split('-')))

    def test_get_license_info(self):
        info = LicenseModel.get_license_info('', '')
        self.assertEqual(info, {})

    def test_get_license_info_default(self):
        info = LicenseModel.get_license_info('', '', fill_defaults=True)
        self.assertEqual(info['users'], 20)
        self.assertEqual(info['valid_till'], 1421884937.512214)
        self.assertEqual(info['email'], 'support@rhodecode.com')
