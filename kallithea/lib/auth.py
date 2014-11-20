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
kallithea.lib.auth
~~~~~~~~~~~~~~~~~~

authentication and permission libraries

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 4, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""
from __future__ import with_statement
import time
import random
import logging
import traceback
import hashlib
import itertools
import collections

from tempfile import _RandomNameSequence
from decorator import decorator

from pylons import url, request
from pylons.controllers.util import abort, redirect
from pylons.i18n.translation import _
from sqlalchemy import or_
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.orm import joinedload

from kallithea import __platform__, is_windows, is_unix
from kallithea.lib.vcs.utils.lazy import LazyProperty
from kallithea.model import meta
from kallithea.model.meta import Session
from kallithea.model.user import UserModel
from kallithea.model.db import User, Repository, Permission, \
    UserToPerm, UserGroupRepoToPerm, UserGroupToPerm, UserGroupMember, \
    RepoGroup, UserGroupRepoGroupToPerm, UserIpMap, UserGroupUserGroupToPerm, \
    UserGroup, UserApiKeys

from kallithea.lib.utils2 import safe_unicode, aslist
from kallithea.lib.utils import get_repo_slug, get_repo_group_slug, \
    get_user_group_slug, conditional_cache
from kallithea.lib.caching_query import FromCache


log = logging.getLogger(__name__)


class PasswordGenerator(object):
    """
    This is a simple class for generating password from different sets of
    characters
    usage::

        passwd_gen = PasswordGenerator()
        #print 8-letter password containing only big and small letters
            of alphabet
        passwd_gen.gen_password(8, passwd_gen.ALPHABETS_BIG_SMALL)
    """
    ALPHABETS_NUM = r'''1234567890'''
    ALPHABETS_SMALL = r'''qwertyuiopasdfghjklzxcvbnm'''
    ALPHABETS_BIG = r'''QWERTYUIOPASDFGHJKLZXCVBNM'''
    ALPHABETS_SPECIAL = r'''`-=[]\;',./~!@#$%^&*()_+{}|:"<>?'''
    ALPHABETS_FULL = ALPHABETS_BIG + ALPHABETS_SMALL \
        + ALPHABETS_NUM + ALPHABETS_SPECIAL
    ALPHABETS_ALPHANUM = ALPHABETS_BIG + ALPHABETS_SMALL + ALPHABETS_NUM
    ALPHABETS_BIG_SMALL = ALPHABETS_BIG + ALPHABETS_SMALL
    ALPHABETS_ALPHANUM_BIG = ALPHABETS_BIG + ALPHABETS_NUM
    ALPHABETS_ALPHANUM_SMALL = ALPHABETS_SMALL + ALPHABETS_NUM

    def __init__(self, passwd=''):
        self.passwd = passwd

    def gen_password(self, length, type_=None):
        if type_ is None:
            type_ = self.ALPHABETS_FULL
        self.passwd = ''.join([random.choice(type_) for _ in xrange(length)])
        return self.passwd


class KallitheaCrypto(object):

    @classmethod
    def hash_string(cls, str_):
        """
        Cryptographic function used for password hashing based on pybcrypt
        or pycrypto in windows

        :param password: password to hash
        """
        if is_windows:
            from hashlib import sha256
            return sha256(str_).hexdigest()
        elif is_unix:
            import bcrypt
            return bcrypt.hashpw(str_, bcrypt.gensalt(10))
        else:
            raise Exception('Unknown or unsupported platform %s' \
                            % __platform__)

    @classmethod
    def hash_check(cls, password, hashed):
        """
        Checks matching password with it's hashed value, runs different
        implementation based on platform it runs on

        :param password: password
        :param hashed: password in hashed form
        """

        if is_windows:
            from hashlib import sha256
            return sha256(password).hexdigest() == hashed
        elif is_unix:
            import bcrypt
            return bcrypt.hashpw(password, hashed) == hashed
        else:
            raise Exception('Unknown or unsupported platform %s' \
                            % __platform__)


def get_crypt_password(password):
    return KallitheaCrypto.hash_string(password)


def check_password(password, hashed):
    return KallitheaCrypto.hash_check(password, hashed)


def generate_api_key(str_, salt=None):
    """
    Generates API KEY from given string

    :param str_:
    :param salt:
    """

    if salt is None:
        salt = _RandomNameSequence().next()

    return hashlib.sha1(str_ + salt).hexdigest()


class CookieStoreWrapper(object):

    def __init__(self, cookie_store):
        self.cookie_store = cookie_store

    def __repr__(self):
        return 'CookieStore<%s>' % (self.cookie_store)

    def get(self, key, other=None):
        if isinstance(self.cookie_store, dict):
            return self.cookie_store.get(key, other)
        elif isinstance(self.cookie_store, AuthUser):
            return self.cookie_store.__dict__.get(key, other)



def _cached_perms_data(user_id, user_is_admin, user_inherit_default_permissions,
                       explicit, algo):
    RK = 'repositories'
    GK = 'repositories_groups'
    UK = 'user_groups'
    GLOBAL = 'global'
    PERM_WEIGHTS = Permission.PERM_WEIGHTS
    permissions = {RK: {}, GK: {}, UK: {}, GLOBAL: set()}

    def _choose_perm(new_perm, cur_perm):
        new_perm_val = PERM_WEIGHTS[new_perm]
        cur_perm_val = PERM_WEIGHTS[cur_perm]
        if algo == 'higherwin':
            if new_perm_val > cur_perm_val:
                return new_perm
            return cur_perm
        elif algo == 'lowerwin':
            if new_perm_val < cur_perm_val:
                return new_perm
            return cur_perm

    #======================================================================
    # fetch default permissions
    #======================================================================
    default_user = User.get_by_username('default', cache=True)
    default_user_id = default_user.user_id

    default_repo_perms = Permission.get_default_perms(default_user_id)
    default_repo_groups_perms = Permission.get_default_group_perms(default_user_id)
    default_user_group_perms = Permission.get_default_user_group_perms(default_user_id)

    if user_is_admin:
        #==================================================================
        # admin user have all default rights for repositories
        # and groups set to admin
        #==================================================================
        permissions[GLOBAL].add('hg.admin')
        permissions[GLOBAL].add('hg.create.write_on_repogroup.true')

        # repositories
        for perm in default_repo_perms:
            r_k = perm.UserRepoToPerm.repository.repo_name
            p = 'repository.admin'
            permissions[RK][r_k] = p

        # repository groups
        for perm in default_repo_groups_perms:
            rg_k = perm.UserRepoGroupToPerm.group.group_name
            p = 'group.admin'
            permissions[GK][rg_k] = p

        # user groups
        for perm in default_user_group_perms:
            u_k = perm.UserUserGroupToPerm.user_group.users_group_name
            p = 'usergroup.admin'
            permissions[UK][u_k] = p
        return permissions

    #==================================================================
    # SET DEFAULTS GLOBAL, REPOS, REPOSITORY GROUPS
    #==================================================================
    uid = user_id

    # default global permissions taken fron the default user
    default_global_perms = UserToPerm.query()\
        .filter(UserToPerm.user_id == default_user_id)\
        .options(joinedload(UserToPerm.permission))

    for perm in default_global_perms:
        permissions[GLOBAL].add(perm.permission.permission_name)

    # defaults for repositories, taken from default user
    for perm in default_repo_perms:
        r_k = perm.UserRepoToPerm.repository.repo_name
        if perm.Repository.private and not (perm.Repository.user_id == uid):
            # disable defaults for private repos,
            p = 'repository.none'
        elif perm.Repository.user_id == uid:
            # set admin if owner
            p = 'repository.admin'
        else:
            p = perm.Permission.permission_name

        permissions[RK][r_k] = p

    # defaults for repository groups taken from default user permission
    # on given group
    for perm in default_repo_groups_perms:
        rg_k = perm.UserRepoGroupToPerm.group.group_name
        p = perm.Permission.permission_name
        permissions[GK][rg_k] = p

    # defaults for user groups taken from default user permission
    # on given user group
    for perm in default_user_group_perms:
        u_k = perm.UserUserGroupToPerm.user_group.users_group_name
        p = perm.Permission.permission_name
        permissions[UK][u_k] = p

    #======================================================================
    # !! OVERRIDE GLOBALS !! with user permissions if any found
    #======================================================================
    # those can be configured from groups or users explicitly
    _configurable = set([
        'hg.fork.none', 'hg.fork.repository',
        'hg.create.none', 'hg.create.repository',
        'hg.usergroup.create.false', 'hg.usergroup.create.true'
    ])

    # USER GROUPS comes first
    # user group global permissions
    user_perms_from_users_groups = Session().query(UserGroupToPerm)\
        .options(joinedload(UserGroupToPerm.permission))\
        .join((UserGroupMember, UserGroupToPerm.users_group_id ==
               UserGroupMember.users_group_id))\
        .filter(UserGroupMember.user_id == uid)\
        .order_by(UserGroupToPerm.users_group_id)\
        .all()
    # need to group here by groups since user can be in more than
    # one group
    _grouped = [[x, list(y)] for x, y in
                itertools.groupby(user_perms_from_users_groups,
                                  lambda x:x.users_group)]
    for gr, perms in _grouped:
        # since user can be in multiple groups iterate over them and
        # select the lowest permissions first (more explicit)
        ##TODO: do this^^
        if not gr.inherit_default_permissions:
            # NEED TO IGNORE all configurable permissions and
            # replace them with explicitly set
            permissions[GLOBAL] = permissions[GLOBAL]\
                                            .difference(_configurable)
        for perm in perms:
            permissions[GLOBAL].add(perm.permission.permission_name)

    # user specific global permissions
    user_perms = Session().query(UserToPerm)\
            .options(joinedload(UserToPerm.permission))\
            .filter(UserToPerm.user_id == uid).all()

    if not user_inherit_default_permissions:
        # NEED TO IGNORE all configurable permissions and
        # replace them with explicitly set
        permissions[GLOBAL] = permissions[GLOBAL]\
                                        .difference(_configurable)

        for perm in user_perms:
            permissions[GLOBAL].add(perm.permission.permission_name)
    ## END GLOBAL PERMISSIONS

    #======================================================================
    # !! PERMISSIONS FOR REPOSITORIES !!
    #======================================================================
    #======================================================================
    # check if user is part of user groups for this repository and
    # fill in his permission from it. _choose_perm decides of which
    # permission should be selected based on selected method
    #======================================================================

    # user group for repositories permissions
    user_repo_perms_from_users_groups = \
     Session().query(UserGroupRepoToPerm, Permission, Repository,)\
        .join((Repository, UserGroupRepoToPerm.repository_id ==
               Repository.repo_id))\
        .join((Permission, UserGroupRepoToPerm.permission_id ==
               Permission.permission_id))\
        .join((UserGroupMember, UserGroupRepoToPerm.users_group_id ==
               UserGroupMember.users_group_id))\
        .filter(UserGroupMember.user_id == uid)\
        .all()

    multiple_counter = collections.defaultdict(int)
    for perm in user_repo_perms_from_users_groups:
        r_k = perm.UserGroupRepoToPerm.repository.repo_name
        multiple_counter[r_k] += 1
        p = perm.Permission.permission_name
        cur_perm = permissions[RK][r_k]

        if perm.Repository.user_id == uid:
            # set admin if owner
            p = 'repository.admin'
        else:
            if multiple_counter[r_k] > 1:
                p = _choose_perm(p, cur_perm)
        permissions[RK][r_k] = p

    # user explicit permissions for repositories, overrides any specified
    # by the group permission
    user_repo_perms = Permission.get_default_perms(uid)
    for perm in user_repo_perms:
        r_k = perm.UserRepoToPerm.repository.repo_name
        cur_perm = permissions[RK][r_k]
        # set admin if owner
        if perm.Repository.user_id == uid:
            p = 'repository.admin'
        else:
            p = perm.Permission.permission_name
            if not explicit:
                p = _choose_perm(p, cur_perm)
        permissions[RK][r_k] = p

    #======================================================================
    # !! PERMISSIONS FOR REPOSITORY GROUPS !!
    #======================================================================
    #======================================================================
    # check if user is part of user groups for this repository groups and
    # fill in his permission from it. _choose_perm decides of which
    # permission should be selected based on selected method
    #======================================================================
    # user group for repo groups permissions
    user_repo_group_perms_from_users_groups = \
     Session().query(UserGroupRepoGroupToPerm, Permission, RepoGroup)\
     .join((RepoGroup, UserGroupRepoGroupToPerm.group_id == RepoGroup.group_id))\
     .join((Permission, UserGroupRepoGroupToPerm.permission_id
            == Permission.permission_id))\
     .join((UserGroupMember, UserGroupRepoGroupToPerm.users_group_id
            == UserGroupMember.users_group_id))\
     .filter(UserGroupMember.user_id == uid)\
     .all()

    multiple_counter = collections.defaultdict(int)
    for perm in user_repo_group_perms_from_users_groups:
        g_k = perm.UserGroupRepoGroupToPerm.group.group_name
        multiple_counter[g_k] += 1
        p = perm.Permission.permission_name
        cur_perm = permissions[GK][g_k]
        if multiple_counter[g_k] > 1:
            p = _choose_perm(p, cur_perm)
        permissions[GK][g_k] = p

    # user explicit permissions for repository groups
    user_repo_groups_perms = Permission.get_default_group_perms(uid)
    for perm in user_repo_groups_perms:
        rg_k = perm.UserRepoGroupToPerm.group.group_name
        p = perm.Permission.permission_name
        cur_perm = permissions[GK][rg_k]
        if not explicit:
            p = _choose_perm(p, cur_perm)
        permissions[GK][rg_k] = p

    #======================================================================
    # !! PERMISSIONS FOR USER GROUPS !!
    #======================================================================
    # user group for user group permissions
    user_group_user_groups_perms = \
     Session().query(UserGroupUserGroupToPerm, Permission, UserGroup)\
     .join((UserGroup, UserGroupUserGroupToPerm.target_user_group_id
            == UserGroup.users_group_id))\
     .join((Permission, UserGroupUserGroupToPerm.permission_id
            == Permission.permission_id))\
     .join((UserGroupMember, UserGroupUserGroupToPerm.user_group_id
            == UserGroupMember.users_group_id))\
     .filter(UserGroupMember.user_id == uid)\
     .all()

    multiple_counter = collections.defaultdict(int)
    for perm in user_group_user_groups_perms:
        g_k = perm.UserGroupUserGroupToPerm.target_user_group.users_group_name
        multiple_counter[g_k] += 1
        p = perm.Permission.permission_name
        cur_perm = permissions[UK][g_k]
        if multiple_counter[g_k] > 1:
            p = _choose_perm(p, cur_perm)
        permissions[UK][g_k] = p

    #user explicit permission for user groups
    user_user_groups_perms = Permission.get_default_user_group_perms(uid)
    for perm in user_user_groups_perms:
        u_k = perm.UserUserGroupToPerm.user_group.users_group_name
        p = perm.Permission.permission_name
        cur_perm = permissions[UK][u_k]
        if not explicit:
            p = _choose_perm(p, cur_perm)
        permissions[UK][u_k] = p

    return permissions


def allowed_api_access(controller_name, whitelist=None, api_key=None):
    """
    Check if given controller_name is in whitelist API access
    """
    if not whitelist:
        from kallithea import CONFIG
        whitelist = aslist(CONFIG.get('api_access_controllers_whitelist'),
                           sep=',')
        log.debug('whitelist of API access is: %s' % (whitelist))
    api_access_valid = controller_name in whitelist
    if api_access_valid:
        log.debug('controller:%s is in API whitelist' % (controller_name))
    else:
        msg = 'controller: %s is *NOT* in API whitelist' % (controller_name)
        if api_key:
            #if we use API key and don't have access it's a warning
            log.warning(msg)
        else:
            log.debug(msg)
    return api_access_valid


class AuthUser(object):
    """
    A simple object that handles all attributes of user in Kallithea

    It does lookup based on API key,given user, or user present in session
    Then it fills all required information for such user. It also checks if
    anonymous access is enabled and if so, it returns default user as logged in
    """

    def __init__(self, user_id=None, api_key=None, username=None, ip_addr=None):

        self.user_id = user_id
        self._api_key = api_key

        self.api_key = None
        self.username = username
        self.ip_addr = ip_addr
        self.name = ''
        self.lastname = ''
        self.email = ''
        self.is_authenticated = False
        self.admin = False
        self.inherit_default_permissions = False

        self.propagate_data()
        self._instance = None

    @LazyProperty
    def permissions(self):
        return self.get_perms(user=self, cache=False)

    @property
    def api_keys(self):
        return self.get_api_keys()

    def propagate_data(self):
        user_model = UserModel()
        self.anonymous_user = User.get_default_user(cache=True)
        is_user_loaded = False

        # lookup by userid
        if self.user_id is not None and self.user_id != self.anonymous_user.user_id:
            log.debug('Auth User lookup by USER ID %s' % self.user_id)
            is_user_loaded = user_model.fill_data(self, user_id=self.user_id)

        # try go get user by api key
        elif self._api_key and self._api_key != self.anonymous_user.api_key:
            log.debug('Auth User lookup by API KEY %s' % self._api_key)
            is_user_loaded = user_model.fill_data(self, api_key=self._api_key)

        # lookup by username
        elif self.username:
            log.debug('Auth User lookup by USER NAME %s' % self.username)
            is_user_loaded = user_model.fill_data(self, username=self.username)
        else:
            log.debug('No data in %s that could been used to log in' % self)

        if not is_user_loaded:
            # if we cannot authenticate user try anonymous
            if self.anonymous_user.active:
                user_model.fill_data(self, user_id=self.anonymous_user.user_id)
                # then we set this user is logged in
                self.is_authenticated = True
            else:
                self.user_id = None
                self.username = None
                self.is_authenticated = False

        if not self.username:
            self.username = 'None'

        log.debug('Auth User is now %s' % self)

    def get_perms(self, user, explicit=True, algo='higherwin', cache=False):
        """
        Fills user permission attribute with permissions taken from database
        works for permissions given for repositories, and for permissions that
        are granted to groups

        :param user: instance of User object from database
        :param explicit: In case there are permissions both for user and a group
            that user is part of, explicit flag will defiine if user will
            explicitly override permissions from group, if it's False it will
            make decision based on the algo
        :param algo: algorithm to decide what permission should be choose if
            it's multiple defined, eg user in two different groups. It also
            decides if explicit flag is turned off how to specify the permission
            for case when user is in a group + have defined separate permission
        """
        user_id = user.user_id
        user_is_admin = user.is_admin
        user_inherit_default_permissions = user.inherit_default_permissions

        log.debug('Getting PERMISSION tree')
        compute = conditional_cache('short_term', 'cache_desc',
                                    condition=cache, func=_cached_perms_data)
        return compute(user_id, user_is_admin,
                       user_inherit_default_permissions, explicit, algo)

    def get_api_keys(self):
        api_keys = [self.api_key]
        for api_key in UserApiKeys.query()\
                .filter(UserApiKeys.user_id == self.user_id)\
                .filter(or_(UserApiKeys.expires == -1,
                            UserApiKeys.expires >= time.time())).all():
            api_keys.append(api_key.api_key)

        return api_keys

    @property
    def is_admin(self):
        return self.admin

    @property
    def repositories_admin(self):
        """
        Returns list of repositories you're an admin of
        """
        return [x[0] for x in self.permissions['repositories'].iteritems()
                if x[1] == 'repository.admin']

    @property
    def repository_groups_admin(self):
        """
        Returns list of repository groups you're an admin of
        """
        return [x[0] for x in self.permissions['repositories_groups'].iteritems()
                if x[1] == 'group.admin']

    @property
    def user_groups_admin(self):
        """
        Returns list of user groups you're an admin of
        """
        return [x[0] for x in self.permissions['user_groups'].iteritems()
                if x[1] == 'usergroup.admin']

    @property
    def ip_allowed(self):
        """
        Checks if ip_addr used in constructor is allowed from defined list of
        allowed ip_addresses for user

        :returns: boolean, True if ip is in allowed ip range
        """
        # check IP
        inherit = self.inherit_default_permissions
        return AuthUser.check_ip_allowed(self.user_id, self.ip_addr,
                                         inherit_from_default=inherit)

    @classmethod
    def check_ip_allowed(cls, user_id, ip_addr, inherit_from_default):
        allowed_ips = AuthUser.get_allowed_ips(user_id, cache=True,
                        inherit_from_default=inherit_from_default)
        if check_ip_access(source_ip=ip_addr, allowed_ips=allowed_ips):
            log.debug('IP:%s is in range of %s' % (ip_addr, allowed_ips))
            return True
        else:
            log.info('Access for IP:%s forbidden, '
                     'not in %s' % (ip_addr, allowed_ips))
            return False

    def __repr__(self):
        return "<AuthUser('id:%s[%s] ip:%s auth:%s')>"\
            % (self.user_id, self.username, self.ip_addr, self.is_authenticated)

    def set_authenticated(self, authenticated=True):
        if self.user_id != self.anonymous_user.user_id:
            self.is_authenticated = authenticated

    def get_cookie_store(self):
        return {'username': self.username,
                'user_id': self.user_id,
                'is_authenticated': self.is_authenticated}

    @classmethod
    def from_cookie_store(cls, cookie_store):
        """
        Creates AuthUser from a cookie store

        :param cls:
        :param cookie_store:
        """
        user_id = cookie_store.get('user_id')
        username = cookie_store.get('username')
        api_key = cookie_store.get('api_key')
        return AuthUser(user_id, api_key, username)

    @classmethod
    def get_allowed_ips(cls, user_id, cache=False, inherit_from_default=False):
        _set = set()

        if inherit_from_default:
            default_ips = UserIpMap.query().filter(UserIpMap.user ==
                                            User.get_default_user(cache=True))
            if cache:
                default_ips = default_ips.options(FromCache("sql_cache_short",
                                                  "get_user_ips_default"))

            # populate from default user
            for ip in default_ips:
                try:
                    _set.add(ip.ip_addr)
                except ObjectDeletedError:
                    # since we use heavy caching sometimes it happens that we get
                    # deleted objects here, we just skip them
                    pass

        user_ips = UserIpMap.query().filter(UserIpMap.user_id == user_id)
        if cache:
            user_ips = user_ips.options(FromCache("sql_cache_short",
                                                  "get_user_ips_%s" % user_id))

        for ip in user_ips:
            try:
                _set.add(ip.ip_addr)
            except ObjectDeletedError:
                # since we use heavy caching sometimes it happens that we get
                # deleted objects here, we just skip them
                pass
        return _set or set(['0.0.0.0/0', '::/0'])


def set_available_permissions(config):
    """
    This function will propagate pylons globals with all available defined
    permission given in db. We don't want to check each time from db for new
    permissions since adding a new permission also requires application restart
    ie. to decorate new views with the newly created permission

    :param config: current pylons config instance

    """
    log.info('getting information about all available permissions')
    try:
        sa = meta.Session
        all_perms = sa.query(Permission).all()
        config['available_permissions'] = [x.permission_name for x in all_perms]
    except Exception:
        log.error(traceback.format_exc())
    finally:
        meta.Session.remove()


#==============================================================================
# CHECK DECORATORS
#==============================================================================
class LoginRequired(object):
    """
    Must be logged in to execute this function else
    redirect to login page

    :param api_access: if enabled this checks only for valid auth token
        and grants access based on valid token
    """

    def __init__(self, api_access=False):
        self.api_access = api_access

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        user = cls.authuser
        loc = "%s:%s" % (cls.__class__.__name__, func.__name__)

        # check if our IP is allowed
        ip_access_valid = True
        if not user.ip_allowed:
            from kallithea.lib import helpers as h
            h.flash(h.literal(_('IP %s not allowed' % (user.ip_addr))),
                    category='warning')
            ip_access_valid = False

        # check if we used an APIKEY and it's a valid one
        # defined whitelist of controllers which API access will be enabled
        _api_key = request.GET.get('api_key', '')
        api_access_valid = allowed_api_access(loc, api_key=_api_key)

        # explicit controller is enabled or API is in our whitelist
        if self.api_access or api_access_valid:
            log.debug('Checking API KEY access for %s' % cls)
            if _api_key and _api_key in user.api_keys:
                api_access_valid = True
                log.debug('API KEY ****%s is VALID' % _api_key[-4:])
            else:
                api_access_valid = False
                if not _api_key:
                    log.debug("API KEY *NOT* present in request")
                else:
                    log.warning("API KEY ****%s *NOT* valid" % _api_key[-4:])

        log.debug('Checking if %s is authenticated @ %s' % (user.username, loc))
        reason = 'RegularAuth' if user.is_authenticated else 'APIAuth'

        if ip_access_valid and (user.is_authenticated or api_access_valid):
            log.info('user %s authenticating with:%s IS authenticated on func %s '
                     % (user, reason, loc)
            )
            return func(*fargs, **fkwargs)
        else:
            log.warning('user %s authenticating with:%s NOT authenticated on func: %s: '
                     'IP_ACCESS:%s API_ACCESS:%s'
                     % (user, reason, loc, ip_access_valid, api_access_valid)
            )
            p = url.current()

            log.debug('redirecting to login page with %s' % p)
            return redirect(url('login_home', came_from=p))


class NotAnonymous(object):
    """
    Must be logged in to execute this function else
    redirect to login page"""

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        self.user = cls.authuser

        log.debug('Checking if user is not anonymous @%s' % cls)

        anonymous = self.user.username == User.DEFAULT_USER

        if anonymous:
            p = url.current()

            import kallithea.lib.helpers as h
            h.flash(_('You need to be a registered user to '
                      'perform this action'),
                    category='warning')
            return redirect(url('login_home', came_from=p))
        else:
            return func(*fargs, **fkwargs)


class PermsDecorator(object):
    """Base class for controller decorators"""

    def __init__(self, *required_perms):
        self.required_perms = set(required_perms)
        self.user_perms = None

    def __call__(self, func):
        return decorator(self.__wrapper, func)

    def __wrapper(self, func, *fargs, **fkwargs):
        cls = fargs[0]
        self.user = cls.authuser
        self.user_perms = self.user.permissions
        log.debug('checking %s permissions %s for %s %s',
           self.__class__.__name__, self.required_perms, cls, self.user)

        if self.check_permissions():
            log.debug('Permission granted for %s %s' % (cls, self.user))
            return func(*fargs, **fkwargs)

        else:
            log.debug('Permission denied for %s %s' % (cls, self.user))
            anonymous = self.user.username == User.DEFAULT_USER

            if anonymous:
                p = url.current()

                import kallithea.lib.helpers as h
                h.flash(_('You need to be a signed in to '
                          'view this page'),
                        category='warning')
                return redirect(url('login_home', came_from=p))

            else:
                # redirect with forbidden ret code
                return abort(403)

    def check_permissions(self):
        """Dummy function for overriding"""
        raise Exception('You have to write this function in child class')


class HasPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates. All of them
    have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        if self.required_perms.issubset(self.user_perms.get('global')):
            return True
        return False


class HasPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates. In order to
    fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        if self.required_perms.intersection(self.user_perms.get('global')):
            return True
        return False


class HasRepoPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates for specific
    repository. All of them have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        repo_name = get_repo_slug(request)
        try:
            user_perms = set([self.user_perms['repositories'][repo_name]])
        except KeyError:
            return False
        if self.required_perms.issubset(user_perms):
            return True
        return False


class HasRepoPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates for specific
    repository. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        repo_name = get_repo_slug(request)
        try:
            user_perms = set([self.user_perms['repositories'][repo_name]])
        except KeyError:
            return False

        if self.required_perms.intersection(user_perms):
            return True
        return False


class HasRepoGroupPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates for specific
    repository group. All of them have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        group_name = get_repo_group_slug(request)
        try:
            user_perms = set([self.user_perms['repositories_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.issubset(user_perms):
            return True
        return False


class HasRepoGroupPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates for specific
    repository group. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        group_name = get_repo_group_slug(request)
        try:
            user_perms = set([self.user_perms['repositories_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.intersection(user_perms):
            return True
        return False


class HasUserGroupPermissionAllDecorator(PermsDecorator):
    """
    Checks for access permission for all given predicates for specific
    user group. All of them have to be meet in order to fulfill the request
    """

    def check_permissions(self):
        group_name = get_user_group_slug(request)
        try:
            user_perms = set([self.user_perms['user_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.issubset(user_perms):
            return True
        return False


class HasUserGroupPermissionAnyDecorator(PermsDecorator):
    """
    Checks for access permission for any of given predicates for specific
    user group. In order to fulfill the request any of predicates must be meet
    """

    def check_permissions(self):
        group_name = get_user_group_slug(request)
        try:
            user_perms = set([self.user_perms['user_groups'][group_name]])
        except KeyError:
            return False

        if self.required_perms.intersection(user_perms):
            return True
        return False


#==============================================================================
# CHECK FUNCTIONS
#==============================================================================
class PermsFunction(object):
    """Base function for other check functions"""

    def __init__(self, *perms):
        self.required_perms = set(perms)
        self.user_perms = None
        self.repo_name = None
        self.group_name = None

    def __call__(self, check_location='', user=None):
        if not user:
            #TODO: remove this someday,put as user as attribute here
            user = request.user

        # init auth user if not already given
        if not isinstance(user, AuthUser):
            user = AuthUser(user.user_id)

        cls_name = self.__class__.__name__
        check_scope = {
            'HasPermissionAll': '',
            'HasPermissionAny': '',
            'HasRepoPermissionAll': 'repo:%s' % self.repo_name,
            'HasRepoPermissionAny': 'repo:%s' % self.repo_name,
            'HasRepoGroupPermissionAll': 'group:%s' % self.group_name,
            'HasRepoGroupPermissionAny': 'group:%s' % self.group_name,
        }.get(cls_name, '?')
        log.debug('checking cls:%s %s usr:%s %s @ %s', cls_name,
                  self.required_perms, user, check_scope,
                  check_location or 'unspecified location')
        if not user:
            log.debug('Empty request user')
            return False
        self.user_perms = user.permissions
        if self.check_permissions():
            log.debug('Permission to %s granted for user: %s @ %s'
                      % (check_scope, user,
                         check_location or 'unspecified location'))
            return True

        else:
            log.debug('Permission to %s denied for user: %s @ %s'
                      % (check_scope, user,
                         check_location or 'unspecified location'))
            return False

    def check_permissions(self):
        """Dummy function for overriding"""
        raise Exception('You have to write this function in child class')


class HasPermissionAll(PermsFunction):
    def check_permissions(self):
        if self.required_perms.issubset(self.user_perms.get('global')):
            return True
        return False


class HasPermissionAny(PermsFunction):
    def check_permissions(self):
        if self.required_perms.intersection(self.user_perms.get('global')):
            return True
        return False


class HasRepoPermissionAll(PermsFunction):
    def __call__(self, repo_name=None, check_location='', user=None):
        self.repo_name = repo_name
        return super(HasRepoPermissionAll, self).__call__(check_location, user)

    def check_permissions(self):
        if not self.repo_name:
            self.repo_name = get_repo_slug(request)

        try:
            self._user_perms = set(
                [self.user_perms['repositories'][self.repo_name]]
            )
        except KeyError:
            return False
        if self.required_perms.issubset(self._user_perms):
            return True
        return False


class HasRepoPermissionAny(PermsFunction):
    def __call__(self, repo_name=None, check_location='', user=None):
        self.repo_name = repo_name
        return super(HasRepoPermissionAny, self).__call__(check_location, user)

    def check_permissions(self):
        if not self.repo_name:
            self.repo_name = get_repo_slug(request)

        try:
            self._user_perms = set(
                [self.user_perms['repositories'][self.repo_name]]
            )
        except KeyError:
            return False
        if self.required_perms.intersection(self._user_perms):
            return True
        return False


class HasRepoGroupPermissionAny(PermsFunction):
    def __call__(self, group_name=None, check_location='', user=None):
        self.group_name = group_name
        return super(HasRepoGroupPermissionAny, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['repositories_groups'][self.group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.intersection(self._user_perms):
            return True
        return False


class HasRepoGroupPermissionAll(PermsFunction):
    def __call__(self, group_name=None, check_location='', user=None):
        self.group_name = group_name
        return super(HasRepoGroupPermissionAll, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['repositories_groups'][self.group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.issubset(self._user_perms):
            return True
        return False


class HasUserGroupPermissionAny(PermsFunction):
    def __call__(self, user_group_name=None, check_location='', user=None):
        self.user_group_name = user_group_name
        return super(HasUserGroupPermissionAny, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['user_groups'][self.user_group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.intersection(self._user_perms):
            return True
        return False


class HasUserGroupPermissionAll(PermsFunction):
    def __call__(self, user_group_name=None, check_location='', user=None):
        self.user_group_name = user_group_name
        return super(HasUserGroupPermissionAll, self).__call__(check_location, user)

    def check_permissions(self):
        try:
            self._user_perms = set(
                [self.user_perms['user_groups'][self.user_group_name]]
            )
        except KeyError:
            return False
        if self.required_perms.issubset(self._user_perms):
            return True
        return False


#==============================================================================
# SPECIAL VERSION TO HANDLE MIDDLEWARE AUTH
#==============================================================================
class HasPermissionAnyMiddleware(object):
    def __init__(self, *perms):
        self.required_perms = set(perms)

    def __call__(self, user, repo_name):
        # repo_name MUST be unicode, since we handle keys in permission
        # dict by unicode
        repo_name = safe_unicode(repo_name)
        usr = AuthUser(user.user_id)
        try:
            self.user_perms = set([usr.permissions['repositories'][repo_name]])
        except Exception:
            log.error('Exception while accessing permissions %s' %
                      traceback.format_exc())
            self.user_perms = set()
        self.username = user.username
        self.repo_name = repo_name
        return self.check_permissions()

    def check_permissions(self):
        log.debug('checking VCS protocol '
                  'permissions %s for user:%s repository:%s', self.user_perms,
                                                self.username, self.repo_name)
        if self.required_perms.intersection(self.user_perms):
            log.debug('Permission to repo: %s granted for user: %s @ %s'
                      % (self.repo_name, self.username, 'PermissionMiddleware'))
            return True
        log.debug('Permission to repo: %s denied for user: %s @ %s'
                  % (self.repo_name, self.username, 'PermissionMiddleware'))
        return False


#==============================================================================
# SPECIAL VERSION TO HANDLE API AUTH
#==============================================================================
class _BaseApiPerm(object):
    def __init__(self, *perms):
        self.required_perms = set(perms)

    def __call__(self, check_location=None, user=None, repo_name=None,
                 group_name=None):
        cls_name = self.__class__.__name__
        check_scope = 'user:%s' % (user)
        if repo_name:
            check_scope += ', repo:%s' % (repo_name)

        if group_name:
            check_scope += ', repo group:%s' % (group_name)

        log.debug('checking cls:%s %s %s @ %s'
                  % (cls_name, self.required_perms, check_scope, check_location))
        if not user:
            log.debug('Empty User passed into arguments')
            return False

        ## process user
        if not isinstance(user, AuthUser):
            user = AuthUser(user.user_id)
        if not check_location:
            check_location = 'unspecified'
        if self.check_permissions(user.permissions, repo_name, group_name):
            log.debug('Permission to %s granted for user: %s @ %s'
                      % (check_scope, user, check_location))
            return True

        else:
            log.debug('Permission to %s denied for user: %s @ %s'
                      % (check_scope, user, check_location))
            return False

    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        """
        implement in child class should return True if permissions are ok,
        False otherwise

        :param perm_defs: dict with permission definitions
        :param repo_name: repo name
        """
        raise NotImplementedError()


class HasPermissionAllApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        if self.required_perms.issubset(perm_defs.get('global')):
            return True
        return False


class HasPermissionAnyApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        if self.required_perms.intersection(perm_defs.get('global')):
            return True
        return False


class HasRepoPermissionAllApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories'][repo_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.issubset(_user_perms):
            return True
        return False


class HasRepoPermissionAnyApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories'][repo_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.intersection(_user_perms):
            return True
        return False


class HasRepoGroupPermissionAnyApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories_groups'][group_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.intersection(_user_perms):
            return True
        return False

class HasRepoGroupPermissionAllApi(_BaseApiPerm):
    def check_permissions(self, perm_defs, repo_name=None, group_name=None):
        try:
            _user_perms = set([perm_defs['repositories_groups'][group_name]])
        except KeyError:
            log.warning(traceback.format_exc())
            return False
        if self.required_perms.issubset(_user_perms):
            return True
        return False

def check_ip_access(source_ip, allowed_ips=None):
    """
    Checks if source_ip is a subnet of any of allowed_ips.

    :param source_ip:
    :param allowed_ips: list of allowed ips together with mask
    """
    from kallithea.lib import ipaddr
    log.debug('checking if ip:%s is subnet of %s' % (source_ip, allowed_ips))
    if isinstance(allowed_ips, (tuple, list, set)):
        for ip in allowed_ips:
            try:
                if ipaddr.IPAddress(source_ip) in ipaddr.IPNetwork(ip):
                    log.debug('IP %s is network %s' %
                              (ipaddr.IPAddress(source_ip), ipaddr.IPNetwork(ip)))
                    return True
                # for any case we cannot determine the IP, don't crash just
                # skip it and log as error, we want to say forbidden still when
                # sending bad IP
            except Exception:
                log.error(traceback.format_exc())
                continue
    return False
