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
kallithea.model.api_key
~~~~~~~~~~~~~~~~~~~~~~~

api key model for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Sep 8, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import with_statement
import time
import logging
import traceback
from sqlalchemy import or_

from kallithea.lib.utils2 import generate_api_key
from kallithea.model import BaseModel
from kallithea.model.db import UserApiKeys
from kallithea.model.meta import Session

log = logging.getLogger(__name__)


class ApiKeyModel(BaseModel):
    cls = UserApiKeys

    def create(self, user, description, lifetime=-1):
        """
        :param user: user or user_id
        :param description: description of ApiKey
        :param lifetime: expiration time in seconds
        """
        user = self._get_user(user)

        new_api_key = UserApiKeys()
        new_api_key.api_key = generate_api_key(user.username)
        new_api_key.user_id = user.user_id
        new_api_key.description = description
        new_api_key.expires = time.time() + (lifetime * 60) if lifetime != -1 else -1
        Session().add(new_api_key)

        return new_api_key

    def delete(self, api_key, user=None):
        """
        Deletes given api_key, if user is set it also filters the object for
        deletion by given user.
        """
        api_key = UserApiKeys.query().filter(UserApiKeys.api_key == api_key)

        if user:
            user = self._get_user(user)
            api_key = api_key.filter(UserApiKeys.user_id == user.user_id)

        api_key = api_key.scalar()
        try:
            Session().delete(api_key)
        except Exception:
            log.error(traceback.format_exc())
            raise

    def get_api_keys(self, user, show_expired=True):
        user = self._get_user(user)
        user_api_keys = UserApiKeys.query()\
            .filter(UserApiKeys.user_id == user.user_id)
        if not show_expired:
            user_api_keys = user_api_keys\
                .filter(or_(UserApiKeys.expires == -1,
                            UserApiKeys.expires >= time.time()))
        return user_api_keys
