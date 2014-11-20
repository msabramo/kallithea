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
kallithea.lib.auth_modules.auth_internal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kallithea authentication plugin for built in internal auth

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Created on Nov 17, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging

from kallithea import EXTERN_TYPE_INTERNAL
from kallithea.lib import auth_modules
from kallithea.lib.compat import formatted_json, hybrid_property
from kallithea.model.db import User

log = logging.getLogger(__name__)


class KallitheaAuthPlugin(auth_modules.KallitheaAuthPluginBase):
    def __init__(self):
        pass

    @hybrid_property
    def name(self):
        return EXTERN_TYPE_INTERNAL

    def settings(self):
        return []

    def user_activation_state(self):
        def_user_perms = User.get_default_user().AuthUser.permissions['global']
        return 'hg.register.auto_activate' in def_user_perms

    def accepts(self, user, accepts_empty=True):
        """
        Custom accepts for this auth that doesn't accept empty users. We
        know that user exisits in database.
        """
        return super(KallitheaAuthPlugin, self).accepts(user,
                                                        accepts_empty=False)

    def auth(self, userobj, username, password, settings, **kwargs):
        if not userobj:
            log.debug('userobj was:%s skipping' % (userobj, ))
            return None
        if userobj.extern_type != self.name:
            log.warning("userobj:%s extern_type mismatch got:`%s` expected:`%s`"
                     % (userobj, userobj.extern_type, self.name))
            return None

        user_attrs = {
            "username": userobj.username,
            "firstname": userobj.firstname,
            "lastname": userobj.lastname,
            "groups": [],
            "email": userobj.email,
            "admin": userobj.admin,
            "active": userobj.active,
            "active_from_extern": userobj.active,
            "extern_name": userobj.user_id,
            'extern_type': userobj.extern_type,
        }

        log.debug(formatted_json(user_attrs))
        if userobj.active:
            from kallithea.lib import auth
            password_match = auth.KallitheaCrypto.hash_check(password, userobj.password)
            if userobj.username == User.DEFAULT_USER and userobj.active:
                log.info('user %s authenticated correctly as anonymous user' %
                         username)
                return user_attrs

            elif userobj.username == username and password_match:
                log.info('user %s authenticated correctly' % user_attrs['username'])
                return user_attrs
            log.error("user %s had a bad password" % username)
            return None
        else:
            log.warning('user %s tried auth but is disabled' % username)
            return None
