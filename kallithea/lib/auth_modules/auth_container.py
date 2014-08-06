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
kallithea.lib.auth_modules.auth_container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kallithea container based authentication plugin

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Created on Nov 17, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging
from kallithea.lib import auth_modules
from kallithea.lib.utils2 import str2bool, safe_unicode
from kallithea.lib.compat import hybrid_property
from kallithea.model.db import User

log = logging.getLogger(__name__)


class KallitheaAuthPlugin(auth_modules.KallitheaExternalAuthPlugin):
    def __init__(self):
        pass

    @hybrid_property
    def name(self):
        return "container"

    @hybrid_property
    def is_container_auth(self):
        return True

    def settings(self):

        settings = [
            {
                "name": "header",
                "validator": self.validators.UnicodeString(strip=True, not_empty=True),
                "type": "string",
                "description": "Header to extract the user from",
                "default": "REMOTE_USER",
                "formname": "Header"
            },
            {
                "name": "fallback_header",
                "validator": self.validators.UnicodeString(strip=True),
                "type": "string",
                "description": "Header to extract the user from when main one fails",
                "default": "HTTP_X_FORWARDED_USER",
                "formname": "Fallback header"
            },
            {
                "name": "clean_username",
                "validator": self.validators.StringBoolean(if_missing=False),
                "type": "bool",
                "description": "Perform cleaning of user, if passed user has @ in username "
                               "then first part before @ is taken. "
                               "If there's \\ in the username only the part after \\ is taken",
                "default": "True",
                "formname": "Clean username"
            },
        ]
        return settings

    def use_fake_password(self):
        return True

    def user_activation_state(self):
        def_user_perms = User.get_default_user().AuthUser.permissions['global']
        return 'hg.extern_activate.auto' in def_user_perms

    def _clean_username(self, username):
        # Removing realm and domain from username
        username = username.partition('@')[0]
        username = username.rpartition('\\')[2]
        return username

    def _get_username(self, environ, settings):
        username = None
        environ = environ or {}
        if not environ:
            log.debug('got empty environ: %s' % environ)

        settings = settings or {}
        if settings.get('header'):
            header = settings.get('header')
            username = environ.get(header)
            log.debug('extracted %s:%s' % (header, username))

        # fallback mode
        if not username and settings.get('fallback_header'):
            header = settings.get('fallback_header')
            username = environ.get(header)
            log.debug('extracted %s:%s' % (header, username))

        if username and str2bool(settings.get('clean_username')):
            log.debug('Received username %s from container' % username)
            username = self._clean_username(username)
            log.debug('New cleanup user is: %s' % username)
        return username

    def get_user(self, username=None, **kwargs):
        """
        Helper method for user fetching in plugins, by default it's using
        simple fetch by username, but this method can be custimized in plugins
        eg. container auth plugin to fetch user by environ params
        :param username: username if given to fetch
        :param kwargs: extra arguments needed for user fetching.
        """
        environ = kwargs.get('environ') or {}
        settings = kwargs.get('settings') or {}
        username = self._get_username(environ, settings)
        # we got the username, so use default method now
        return super(KallitheaAuthPlugin, self).get_user(username)

    def auth(self, userobj, username, password, settings, **kwargs):
        """
        Get's the container_auth username (or email). It tries to get username
        from REMOTE_USER if this plugin is enabled, if that fails
        it tries to get username from HTTP_X_FORWARDED_USER if fallback header
        is set. clean_username extracts the username from this data if it's
        having @ in it.
        Return None on failure. On success, return a dictionary of the form:

            see: KallitheaAuthPluginBase.auth_func_attrs

        :param userobj:
        :param username:
        :param password:
        :param settings:
        :param kwargs:
        """
        environ = kwargs.get('environ')
        if not environ:
            log.debug('Empty environ data skipping...')
            return None

        if not userobj:
            userobj = self.get_user('', environ=environ, settings=settings)

        # we don't care passed username/password for container auth plugins.
        # only way to log in is using environ
        username = None
        if userobj:
            username = getattr(userobj, 'username')

        if not username:
            # we don't have any objects in DB user doesn't exist extrac username
            # from environ based on the settings
            username = self._get_username(environ, settings)

        # if cannot fetch username, it's a no-go for this plugin to proceed
        if not username:
            return None

        # old attrs fetched from Kallithea database
        admin = getattr(userobj, 'admin', False)
        active = getattr(userobj, 'active', True)
        email = getattr(userobj, 'email', '')
        firstname = getattr(userobj, 'firstname', '')
        lastname = getattr(userobj, 'lastname', '')
        extern_type = getattr(userobj, 'extern_type', '')

        user_attrs = {
            'username': username,
            'firstname': safe_unicode(firstname or username),
            'lastname': safe_unicode(lastname or ''),
            'groups': [],
            'email': email or '',
            'admin': admin or False,
            'active': active,
            'active_from_extern': True,
            'extern_name': username,
            'extern_type': extern_type,
        }

        log.info('user `%s` authenticated correctly' % user_attrs['username'])
        return user_attrs
