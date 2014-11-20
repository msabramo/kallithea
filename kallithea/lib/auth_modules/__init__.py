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
Authentication modules
"""

import logging
import traceback

from kallithea import EXTERN_TYPE_INTERNAL
from kallithea.lib.compat import importlib
from kallithea.lib.utils2 import str2bool
from kallithea.lib.compat import formatted_json, hybrid_property
from kallithea.lib.auth import PasswordGenerator
from kallithea.model.user import UserModel
from kallithea.model.db import Setting, User
from kallithea.model.meta import Session
from kallithea.model.user_group import UserGroupModel

log = logging.getLogger(__name__)


class LazyFormencode(object):
    def __init__(self, formencode_obj, *args, **kwargs):
        self.formencode_obj = formencode_obj
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        from inspect import isfunction
        formencode_obj = self.formencode_obj
        if isfunction(formencode_obj):
            #case we wrap validators into functions
            formencode_obj = self.formencode_obj(*args, **kwargs)
        return formencode_obj(*self.args, **self.kwargs)


class KallitheaAuthPluginBase(object):
    auth_func_attrs = {
        "username": "unique username",
        "firstname": "first name",
        "lastname": "last name",
        "email": "email address",
        "groups": '["list", "of", "groups"]',
        "extern_name": "name in external source of record",
        "extern_type": "type of external source of record",
        "admin": 'True|False defines if user should be Kallithea super admin',
        "active": 'True|False defines active state of user internally for Kallithea',
        "active_from_extern": "True|False\None, active state from the external auth, "
                              "None means use definition from Kallithea extern_type active value"
    }

    @property
    def validators(self):
        """
        Exposes Kallithea validators modules
        """
        # this is a hack to overcome issues with pylons threadlocals and
        # translator object _() not beein registered properly.
        class LazyCaller(object):
            def __init__(self, name):
                self.validator_name = name

            def __call__(self, *args, **kwargs):
                from kallithea.model import validators as v
                obj = getattr(v, self.validator_name)
                #log.debug('Initializing lazy formencode object: %s' % obj)
                return LazyFormencode(obj, *args, **kwargs)


        class ProxyGet(object):
            def __getattribute__(self, name):
                return LazyCaller(name)

        return ProxyGet()

    @hybrid_property
    def name(self):
        """
        Returns the name of this authentication plugin.

        :returns: string
        """
        raise NotImplementedError("Not implemented in base class")

    @hybrid_property
    def is_container_auth(self):
        """
        Returns bool if this module uses container auth.

        This property will trigger an automatic call to authenticate on
        a visit to the website or during a push/pull.

        :returns: bool
        """
        return False

    def accepts(self, user, accepts_empty=True):
        """
        Checks if this authentication module should accept a request for
        the current user.

        :param user: user object fetched using plugin's get_user() method.
        :param accepts_empty: if True accepts don't allow the user to be empty
        :returns: boolean
        """
        plugin_name = self.name
        if not user and not accepts_empty:
            log.debug('User is empty not allowed to authenticate')
            return False

        if user and user.extern_type and user.extern_type != plugin_name:
            log.debug('User %s should authenticate using %s this is %s, skipping'
                      % (user, user.extern_type, plugin_name))

            return False
        return True

    def get_user(self, username=None, **kwargs):
        """
        Helper method for user fetching in plugins, by default it's using
        simple fetch by username, but this method can be custimized in plugins
        eg. container auth plugin to fetch user by environ params

        :param username: username if given to fetch from database
        :param kwargs: extra arguments needed for user fetching.
        """
        user = None
        log.debug('Trying to fetch user `%s` from Kallithea database'
                  % (username))
        if username:
            user = User.get_by_username(username)
            if not user:
                log.debug('Fallback to fetch user in case insensitive mode')
                user = User.get_by_username(username, case_insensitive=True)
        else:
            log.debug('provided username:`%s` is empty skipping...' % username)
        return user

    def settings(self):
        """
        Return a list of the form:
        [
            {
                "name": "OPTION_NAME",
                "type": "[bool|password|string|int|select]",
                ["values": ["opt1", "opt2", ...]]
                "validator": "expr"
                "description": "A short description of the option" [,
                "default": Default Value],
                ["formname": "Friendly Name for Forms"]
            } [, ...]
        ]

        This is used to interrogate the authentication plugin as to what
        settings it expects to be present and configured.

        'type' is a shorthand notation for what kind of value this option is.
        This is primarily used by the auth web form to control how the option
        is configured.
                bool : checkbox
                password : password input box
                string : input box
                select : single select dropdown

        'validator' is an lazy instantiated form field validator object, ala
        formencode. You need to *call* this object to init the validators.
        All calls to Kallithea validators should be used through self.validators
        which is a lazy loading proxy of formencode module.
        """
        raise NotImplementedError("Not implemented in base class")

    def plugin_settings(self):
        """
        This method is called by the authentication framework, not the .settings()
        method. This method adds a few default settings (e.g., "active"), so that
        plugin authors don't have to maintain a bunch of boilerplate.

        OVERRIDING THIS METHOD WILL CAUSE YOUR PLUGIN TO FAIL.
        """

        rcsettings = self.settings()
        rcsettings.insert(0, {
            "name": "enabled",
            "validator": self.validators.StringBoolean(if_missing=False),
            "type": "bool",
            "description": "Enable or Disable this Authentication Plugin",
            "formname": "Enabled"
            }
        )
        return rcsettings

    def user_activation_state(self):
        """
        Defines user activation state when creating new users

        :returns: boolean
        """
        raise NotImplementedError("Not implemented in base class")

    def auth(self, userobj, username, passwd, settings, **kwargs):
        """
        Given a user object (which may be null), username, a plaintext password,
        and a settings object (containing all the keys needed as listed in settings()),
        authenticate this user's login attempt.

        Return None on failure. On success, return a dictionary of the form:

            see: KallitheaAuthPluginBase.auth_func_attrs
        This is later validated for correctness
        """
        raise NotImplementedError("not implemented in base class")

    def _authenticate(self, userobj, username, passwd, settings, **kwargs):
        """
        Wrapper to call self.auth() that validates call on it

        :param userobj: userobj
        :param username: username
        :param passwd: plaintext password
        :param settings: plugin settings
        """
        auth = self.auth(userobj, username, passwd, settings, **kwargs)
        if auth:
            return self._validate_auth_return(auth)
        return auth

    def _validate_auth_return(self, ret):
        if not isinstance(ret, dict):
            raise Exception('returned value from auth must be a dict')
        for k in self.auth_func_attrs:
            if k not in ret:
                raise Exception('Missing %s attribute from returned data' % k)
        return ret


class KallitheaExternalAuthPlugin(KallitheaAuthPluginBase):
    def use_fake_password(self):
        """
        Return a boolean that indicates whether or not we should set the user's
        password to a random value when it is authenticated by this plugin.
        If your plugin provides authentication, then you will generally want this.

        :returns: boolean
        """
        raise NotImplementedError("Not implemented in base class")

    def _authenticate(self, userobj, username, passwd, settings, **kwargs):
        auth = super(KallitheaExternalAuthPlugin, self)._authenticate(
            userobj, username, passwd, settings, **kwargs)
        if auth:
            # maybe plugin will clean the username ?
            # we should use the return value
            username = auth['username']
            # if user is not active from our extern type we should fail to authe
            # this can prevent from creating users in Kallithea when using
            # external authentication, but if it's inactive user we shouldn't
            # create that user anyway
            if auth['active_from_extern'] is False:
                log.warning("User %s authenticated against %s, but is inactive"
                            % (username, self.__module__))
                return None

            if self.use_fake_password():
                # Randomize the PW because we don't need it, but don't want
                # them blank either
                passwd = PasswordGenerator().gen_password(length=8)

            log.debug('Updating or creating user info from %s plugin'
                      % self.name)
            user = UserModel().create_or_update(
                username=username,
                password=passwd,
                email=auth["email"],
                firstname=auth["firstname"],
                lastname=auth["lastname"],
                active=auth["active"],
                admin=auth["admin"],
                extern_name=auth["extern_name"],
                extern_type=self.name
            )
            Session().flush()
            # enforce user is just in given groups, all of them has to be ones
            # created from plugins. We store this info in _group_data JSON field
            try:
                groups = auth['groups'] or []
                UserGroupModel().enforce_groups(user, groups, self.name)
            except Exception:
                # for any reason group syncing fails, we should proceed with login
                log.error(traceback.format_exc())
            Session().commit()
        return auth


def importplugin(plugin):
    """
    Imports and returns the authentication plugin in the module named by plugin
    (e.g., plugin='kallithea.lib.auth_modules.auth_internal'). Returns the
    KallitheaAuthPluginBase subclass on success, raises exceptions on failure.

    raises:
        AttributeError -- no KallitheaAuthPlugin class in the module
        TypeError -- if the KallitheaAuthPlugin is not a subclass of ours KallitheaAuthPluginBase
        ImportError -- if we couldn't import the plugin at all
    """
    log.debug("Importing %s" % plugin)
    if not plugin.startswith(u'kallithea.lib.auth_modules.auth_'):
        parts = plugin.split(u'.lib.auth_modules.auth_', 1)
        if len(parts) == 2:
            _module, pn = parts
            if pn == EXTERN_TYPE_INTERNAL:
                pn = "internal"
            plugin = u'kallithea.lib.auth_modules.auth_' + pn
    PLUGIN_CLASS_NAME = "KallitheaAuthPlugin"
    try:
        module = importlib.import_module(plugin)
    except (ImportError, TypeError):
        log.error(traceback.format_exc())
        # TODO: make this more error prone, if by some accident we screw up
        # the plugin name, the crash is preatty bad and hard to recover
        raise

    log.debug("Loaded auth plugin from %s (module:%s, file:%s)"
              % (plugin, module.__name__, module.__file__))

    pluginclass = getattr(module, PLUGIN_CLASS_NAME)
    if not issubclass(pluginclass, KallitheaAuthPluginBase):
        raise TypeError("Authentication class %s.KallitheaAuthPlugin is not "
                        "a subclass of %s" % (plugin, KallitheaAuthPluginBase))
    return pluginclass


def loadplugin(plugin):
    """
    Loads and returns an instantiated authentication plugin.

        see: importplugin
    """
    plugin = importplugin(plugin)()
    if plugin.plugin_settings.im_func != KallitheaAuthPluginBase.plugin_settings.im_func:
        raise TypeError("Authentication class %s.KallitheaAuthPluginBase "
                        "has overriden the plugin_settings method, which is "
                        "forbidden." % plugin)
    return plugin


def authenticate(username, password, environ=None):
    """
    Authentication function used for access control,
    It tries to authenticate based on enabled authentication modules.

    :param username: username can be empty for container auth
    :param password: password can be empty for container auth
    :param environ: environ headers passed for container auth
    :returns: None if auth failed, plugin_user dict if auth is correct
    """

    auth_plugins = Setting.get_auth_plugins()
    log.debug('Authentication against %s plugins' % (auth_plugins,))
    for module in auth_plugins:
        try:
            plugin = loadplugin(module)
        except (ImportError, AttributeError, TypeError), e:
            raise ImportError('Failed to load authentication module %s : %s'
                              % (module, str(e)))
        log.debug('Trying authentication using ** %s **' % (module,))
        # load plugin settings from Kallithea database
        plugin_name = plugin.name
        plugin_settings = {}
        for v in plugin.plugin_settings():
            conf_key = "auth_%s_%s" % (plugin_name, v["name"])
            setting = Setting.get_by_name(conf_key)
            plugin_settings[v["name"]] = setting.app_settings_value if setting else None
        log.debug('Plugin settings \n%s' % formatted_json(plugin_settings))

        if not str2bool(plugin_settings["enabled"]):
            log.info("Authentication plugin %s is disabled, skipping for %s"
                     % (module, username))
            continue

        # use plugin's method of user extraction.
        user = plugin.get_user(username, environ=environ,
                               settings=plugin_settings)
        log.debug('Plugin %s extracted user is `%s`' % (module, user))
        if not plugin.accepts(user):
            log.debug('Plugin %s does not accept user `%s` for authentication'
                      % (module, user))
            continue
        else:
            log.debug('Plugin %s accepted user `%s` for authentication'
                      % (module, user))

        log.info('Authenticating user using %s plugin' % plugin.__module__)
        # _authenticate is a wrapper for .auth() method of plugin.
        # it checks if .auth() sends proper data. for KallitheaExternalAuthPlugin
        # it also maps users to Database and maps the attributes returned
        # from .auth() to Kallithea database. If this function returns data
        # then auth is correct.
        plugin_user = plugin._authenticate(user, username, password,
                                           plugin_settings,
                                           environ=environ or {})
        log.debug('PLUGIN USER DATA: %s' % plugin_user)

        if plugin_user:
            log.debug('Plugin returned proper authentication data')
            return plugin_user

        # we failed to Auth because .auth() method didn't return proper the user
        log.warning("User `%s` failed to authenticate against %s"
                    % (username, plugin.__module__))
    return None
