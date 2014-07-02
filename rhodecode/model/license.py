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
"""
rhodecode.model.license
~~~~~~~~~~~~~~~~~~~~~~~

Model for licenses


:created_on: Aug 1, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH.
:license: GPLv3, see LICENSE for more details.
"""

import uuid
import base64
import time
import logging
import traceback

from Crypto import Random
from Crypto.Cipher import AES

import rhodecode
from rhodecode.lib.compat import json
from rhodecode.model import BaseModel
from rhodecode.model.db import RhodeCodeSetting

log = logging.getLogger(__name__)

BLOCK_SIZE = 32


def pad(s):
    return (s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) *
            chr(BLOCK_SIZE - len(s) % BLOCK_SIZE))


def unpad(s):
    return s[0:-ord(s[-1])]


class LicenseModel(BaseModel):

    cls = RhodeCodeSetting

    def __init__(self, sa=None, key=None):
        super(LicenseModel, self).__init__(sa=sa)
        if not key:
            key = rhodecode.CONFIG.get('license_token')

        if not key:
            raise TypeError('Missing encryption key: %s' % key)
        if not isinstance(key, basestring):
            raise TypeError('Encryption key is bad type, got %s '
                            'expected basestring' % type(key))
        #strip dashes
        self.key = key.replace('-', '')

    @classmethod
    def generate_license_token(cls):
        tok_len = 4
        hex_token = uuid.uuid1().hex
        num_pools = [hex_token[start:start+tok_len]
                     for start in range(0, len(hex_token), tok_len)]
        return u'-'.join(num_pools[:4])

    @classmethod
    def get_default_license(cls):

        key = 'abra-cada-bra1-rce3'
        enc_license_key = ('''
            0HBgVSMJgapshyHBZGiSj/pqSLkO8BmkbSnFDw8j+e854FkSJuVyUhIyUSFgs5mJ+P
            KGknkw/LOf0pKLRZ7EZiFW+lkrv99UaS395FCp4J+ymdg7YdIdYtc0FZ8TcZjXrV3y
            ORR3Klsjf7PUV6XVYSU6CAMx5SyK78n3JwYLclCnog1lD4kwHEFJH+OD5jFG3OT9eN
            Kd0c1rVIJbbkPfppVIa4twr52bXWjueOpamdFI7DOJtlse9XyY1axgGNVQDtgRlWi5
            YmtP8OfT+Rq9SaCMQzPq3R42/YWHHrG1fhEMO7DAuruyLASoXROAo+hZmDoWYiqOP2
            vtJk/vc6WTB0Ro5zBWznFvkvTPzpFNf+A4FlQzQrVLjVOdIKncyJLx7QFHYFWT9ewD
            Abr3XpaN5brqe97hDslN/8uKZabUydYI4dKDYkuc5+WAOfPGuqM/CwIPjZQ6K8ivJK
            yX3CHBThwQuJtQY85GHPte0fT0bHoQyLIBwwYa76/pdm4eTaUrMZbj2HipDGTRO6BU
            DaDIdw5YiczQ+Jec5phmqwbJ5Z/uXzdV6dhFLDTaiQ+PSkRLg9F1/cPZZxYOo8Jatn
            6pSQvmzi4ALTsaPIGGyu5aazPRB0Wz7g2tyPfUcAP5rzS0aWIdoszsAXizBiJdKgr4
            X2SlOqJ3MYfen4rvLbIQwV2IiRJdtv1QoFGAyyGfDtGzYruZbpfQcouhwRJbaESTwB
            0WXMa73Q2jw59GiTB5C4U=''')
        return json.loads(LicenseModel(key=key).decrypt(enc_license_key))

    @classmethod
    def get_license_info(cls, license_token, enc_license_key, safe=True,
                         fill_defaults=False):
        license_info = {}
        if fill_defaults:
            license_info = cls.get_default_license()
        try:
            if license_token and enc_license_key:
                license_info = json.loads(
                    LicenseModel(key=license_token).decrypt(enc_license_key))
        except Exception, e:
            log.error(traceback.format_exc())
            if not safe:
                raise
        return license_info

    @classmethod
    def get_license_key(cls):
        defaults = RhodeCodeSetting.get_app_settings()
        return defaults.get('rhodecode_license_key')

    def encrypt(self, text, key=None):
        if not isinstance(text, basestring):
            raise TypeError('Encrypt can only work on unicode or '
                            'string, got %s' % type(text))
        if not key:
            key = self.key
        padded_text = pad(text)
        IV = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, IV)
        return base64.b64encode(IV + cipher.encrypt(padded_text))

    def decrypt(self, enc_text, key=None):
        if not isinstance(enc_text, (unicode, str)):
            raise TypeError('Encrypt can only work on unicode or '
                            'string, got %s' % type(enc_text))
        if not key:
            key = self.key
        enc = base64.b64decode(enc_text)
        iv = enc[:16]  # iv is stored
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc[16:]))

    def generate_signature(self, license_key, sig_key):
        copy = license_key.copy()
        del copy['signature']
        return self.encrypt(json.dumps(copy), key=sig_key)

    def verify(self, enc_text, sig_key):
        if not isinstance(enc_text, basestring):
            raise TypeError('Encrypt can only work on unicode or '
                            'string, got %s' % type(enc_text))

        decrypted = json.loads(self.decrypt(enc_text))
        try:
            signature = json.loads(self.decrypt(decrypted['signature'], sig_key))
        except Exception:
            signature = '-- decryption error --'

        del decrypted['signature']
        #TODO: write better diff display
        if decrypted != signature:
            raise TypeError('Signature mismatch got %s[%s] vs %s[%s]'
                    % (decrypted, type(decrypted), signature, type(signature)))
        return signature
