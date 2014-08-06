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
kallithea.lib.auth_pam
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kallithea authentication library for PAM

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Created on Apr 09, 2013
:author: Alexey Larikov
"""

import logging
import time
import pam
import pwd
import grp
import re
import socket
import threading

from kallithea.lib import auth_modules
from kallithea.lib.compat import formatted_json, hybrid_property

log = logging.getLogger(__name__)

# Cache to store PAM authenticated users
_auth_cache = dict()
_pam_lock = threading.Lock()


class KallitheaAuthPlugin(auth_modules.KallitheaExternalAuthPlugin):
    # PAM authnetication can be slow. Repository operations involve a lot of
    # auth calls. Little caching helps speedup push/pull operations significantly
    AUTH_CACHE_TTL = 4

    def __init__(self):
        global _auth_cache
        ts = time.time()
        cleared_cache = dict(
            [(k, v) for (k, v) in _auth_cache.items() if
             (v + KallitheaAuthPlugin.AUTH_CACHE_TTL > ts)])
        _auth_cache = cleared_cache

    @hybrid_property
    def name(self):
        return "pam"

    def settings(self):
        settings = [
            {
                "name": "service",
                "validator": self.validators.UnicodeString(strip=True),
                "type": "string",
                "description": "PAM service name to use for authentication",
                "default": "login",
                "formname": "PAM service name"
            },
            {
                "name": "gecos",
                "validator": self.validators.UnicodeString(strip=True),
                "type": "string",
                "description": "Regex for extracting user name/email etc "
                               "from Unix userinfo",
                "default": "(?P<last_name>.+),\s*(?P<first_name>\w+)",
                "formname": "Gecos Regex"
            }
        ]
        return settings

    def use_fake_password(self):
        return True

    def auth(self, userobj, username, password, settings, **kwargs):
        if username not in _auth_cache:
            # Need lock here, as PAM authentication is not thread safe
            _pam_lock.acquire()
            try:
                auth_result = pam.authenticate(username, password,
                                               settings["service"])
                # cache result only if we properly authenticated
                if auth_result:
                    _auth_cache[username] = time.time()
            finally:
                _pam_lock.release()

            if not auth_result:
                log.error("PAM was unable to authenticate user: %s" % (username,))
                return None
        else:
            log.debug("Using cached auth for user: %s" % (username,))

        # old attrs fetched from Kallithea database
        admin = getattr(userobj, 'admin', False)
        active = getattr(userobj, 'active', True)
        email = getattr(userobj, 'email', '') or "%s@%s" % (username, socket.gethostname())
        firstname = getattr(userobj, 'firstname', '')
        lastname = getattr(userobj, 'lastname', '')
        extern_type = getattr(userobj, 'extern_type', '')

        user_attrs = {
            'username': username,
            'firstname': firstname,
            'lastname': lastname,
            'groups': [g.gr_name for g in grp.getgrall() if username in g.gr_mem],
            'email': email,
            'admin': admin,
            'active': active,
            "active_from_extern": None,
            'extern_name': username,
            'extern_type': extern_type,
        }

        try:
            user_data = pwd.getpwnam(username)
            regex = settings["gecos"]
            match = re.search(regex, user_data.pw_gecos)
            if match:
                user_attrs["firstname"] = match.group('first_name')
                user_attrs["lastname"] = match.group('last_name')
        except Exception:
            log.warning("Cannot extract additional info for PAM user")
            pass

        log.debug("pamuser: \n%s" % formatted_json(user_attrs))
        log.info('user %s authenticated correctly' % user_attrs['username'])
        return user_attrs
