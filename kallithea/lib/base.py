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
kallithea.lib.base
~~~~~~~~~~~~~~~~~~

The base Controller API
Provides the BaseController class for subclassing. And usage in different
controllers

:created_on: Oct 06, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH.
:license: GPLv3, see LICENSE for more details.
"""

import logging
import time
import traceback

from paste.auth.basic import AuthBasicAuthenticator
from paste.httpexceptions import HTTPUnauthorized, HTTPForbidden
from paste.httpheaders import WWW_AUTHENTICATE, AUTHORIZATION

from pylons import config, tmpl_context as c, request, session, url
from pylons.controllers import WSGIController
from pylons.controllers.util import redirect
from pylons.templating import render_mako as render  # don't remove this import

from kallithea import __version__, BACKENDS

from kallithea.lib.utils2 import str2bool, safe_unicode, AttributeDict,\
    safe_str, safe_int
from kallithea.lib import auth_modules
from kallithea.lib.auth import AuthUser, HasPermissionAnyMiddleware, CookieStoreWrapper
from kallithea.lib.utils import get_repo_slug
from kallithea.lib.exceptions import UserCreationError
from kallithea.model import meta

from kallithea.model.db import Repository, RhodeCodeUi, User, RhodeCodeSetting
from kallithea.model.notification import NotificationModel
from kallithea.model.scm import ScmModel
from kallithea.model.meta import Session

log = logging.getLogger(__name__)


def _filter_proxy(ip):
    """
    HEADERS can have multiple ips inside the left-most being the original
    client, and each successive proxy that passed the request adding the IP
    address where it received the request from.

    :param ip:
    """
    if ',' in ip:
        _ips = ip.split(',')
        _first_ip = _ips[0].strip()
        log.debug('Got multiple IPs %s, using %s' % (','.join(_ips), _first_ip))
        return _first_ip
    return ip


def _get_ip_addr(environ):
    proxy_key = 'HTTP_X_REAL_IP'
    proxy_key2 = 'HTTP_X_FORWARDED_FOR'
    def_key = 'REMOTE_ADDR'

    ip = environ.get(proxy_key)
    if ip:
        return _filter_proxy(ip)

    ip = environ.get(proxy_key2)
    if ip:
        return _filter_proxy(ip)

    ip = environ.get(def_key, '0.0.0.0')
    return _filter_proxy(ip)


def _get_access_path(environ):
    path = environ.get('PATH_INFO')
    org_req = environ.get('pylons.original_request')
    if org_req:
        path = org_req.environ.get('PATH_INFO')
    return path


class BasicAuth(AuthBasicAuthenticator):

    def __init__(self, realm, authfunc, auth_http_code=None):
        self.realm = realm
        self.authfunc = authfunc
        self._rc_auth_http_code = auth_http_code

    def build_authentication(self):
        head = WWW_AUTHENTICATE.tuples('Basic realm="%s"' % self.realm)
        if self._rc_auth_http_code and self._rc_auth_http_code == '403':
            # return 403 if alternative http return code is specified in
            # RhodeCode config
            return HTTPForbidden(headers=head)
        return HTTPUnauthorized(headers=head)

    def authenticate(self, environ):
        authorization = AUTHORIZATION(environ)
        if not authorization:
            return self.build_authentication()
        (authmeth, auth) = authorization.split(' ', 1)
        if 'basic' != authmeth.lower():
            return self.build_authentication()
        auth = auth.strip().decode('base64')
        _parts = auth.split(':', 1)
        if len(_parts) == 2:
            username, password = _parts
            if self.authfunc(username, password, environ):
                return username
        return self.build_authentication()

    __call__ = authenticate


class BaseVCSController(object):

    def __init__(self, application, config):
        self.application = application
        self.config = config
        # base path of repo locations
        self.basepath = self.config['base_path']
        #authenticate this VCS request using authfunc
        self.authenticate = BasicAuth('', auth_modules.authenticate,
                                      config.get('auth_ret_code'))
        self.ip_addr = '0.0.0.0'

    def _handle_request(self, environ, start_response):
        raise NotImplementedError()

    def _get_by_id(self, repo_name):
        """
        Gets a special pattern _<ID> from clone url and tries to replace it
        with a repository_name for support of _<ID> non changable urls

        :param repo_name:
        """

        data = repo_name.split('/')
        if len(data) >= 2:
            from kallithea.lib.utils import get_repo_by_id
            by_id_match = get_repo_by_id(repo_name)
            if by_id_match:
                data[1] = by_id_match

        return '/'.join(data)

    def _invalidate_cache(self, repo_name):
        """
        Set's cache for this repository for invalidation on next access

        :param repo_name: full repo name, also a cache key
        """
        ScmModel().mark_for_invalidation(repo_name)

    def _check_permission(self, action, user, repo_name, ip_addr=None):
        """
        Checks permissions using action (push/pull) user and repository
        name

        :param action: push or pull action
        :param user: user instance
        :param repo_name: repository name
        """
        # check IP
        inherit = user.inherit_default_permissions
        ip_allowed = AuthUser.check_ip_allowed(user.user_id, ip_addr,
                                               inherit_from_default=inherit)
        if ip_allowed:
            log.info('Access for IP:%s allowed' % (ip_addr,))
        else:
            return False

        if action == 'push':
            if not HasPermissionAnyMiddleware('repository.write',
                                              'repository.admin')(user,
                                                                  repo_name):
                return False

        else:
            #any other action need at least read permission
            if not HasPermissionAnyMiddleware('repository.read',
                                              'repository.write',
                                              'repository.admin')(user,
                                                                  repo_name):
                return False

        return True

    def _get_ip_addr(self, environ):
        return _get_ip_addr(environ)

    def _check_ssl(self, environ, start_response):
        """
        Checks the SSL check flag and returns False if SSL is not present
        and required True otherwise
        """
        org_proto = environ['wsgi._org_proto']
        #check if we have SSL required  ! if not it's a bad request !
        require_ssl = str2bool(RhodeCodeUi.get_by_key('push_ssl').ui_value)
        if require_ssl and org_proto == 'http':
            log.debug('proto is %s and SSL is required BAD REQUEST !'
                      % org_proto)
            return False
        return True

    def _check_locking_state(self, environ, action, repo, user_id):
        """
        Checks locking on this repository, if locking is enabled and lock is
        present returns a tuple of make_lock, locked, locked_by.
        make_lock can have 3 states None (do nothing) True, make lock
        False release lock, This value is later propagated to hooks, which
        do the locking. Think about this as signals passed to hooks what to do.

        """
        locked = False  # defines that locked error should be thrown to user
        make_lock = None
        repo = Repository.get_by_repo_name(repo)
        user = User.get(user_id)

        # this is kind of hacky, but due to how mercurial handles client-server
        # server see all operation on changeset; bookmarks, phases and
        # obsolescence marker in different transaction, we don't want to check
        # locking on those
        obsolete_call = environ['QUERY_STRING'] in ['cmd=listkeys',]
        locked_by = repo.locked
        if repo and repo.enable_locking and not obsolete_call:
            if action == 'push':
                #check if it's already locked !, if it is compare users
                user_id, _date = repo.locked
                if user.user_id == user_id:
                    log.debug('Got push from user %s, now unlocking' % (user))
                    # unlock if we have push from user who locked
                    make_lock = False
                else:
                    # we're not the same user who locked, ban with 423 !
                    locked = True
            if action == 'pull':
                if repo.locked[0] and repo.locked[1]:
                    locked = True
                else:
                    log.debug('Setting lock on repo %s by %s' % (repo, user))
                    make_lock = True

        else:
            log.debug('Repository %s do not have locking enabled' % (repo))
        log.debug('FINAL locking values make_lock:%s,locked:%s,locked_by:%s'
                  % (make_lock, locked, locked_by))
        return make_lock, locked, locked_by

    def __call__(self, environ, start_response):
        start = time.time()
        try:
            return self._handle_request(environ, start_response)
        finally:
            log = logging.getLogger('kallithea.' + self.__class__.__name__)
            log.debug('Request time: %.3fs' % (time.time() - start))
            meta.Session.remove()


class BaseController(WSGIController):

    def __before__(self):
        """
        __before__ is called before controller methods and after __call__
        """
        c.rhodecode_version = __version__
        rc_config = RhodeCodeSetting.get_app_settings()

        # Visual options
        c.visual = AttributeDict({})

        ## DB stored
        c.visual.show_public_icon = str2bool(rc_config.get('rhodecode_show_public_icon'))
        c.visual.show_private_icon = str2bool(rc_config.get('rhodecode_show_private_icon'))
        c.visual.stylify_metatags = str2bool(rc_config.get('rhodecode_stylify_metatags'))
        c.visual.dashboard_items = safe_int(rc_config.get('rhodecode_dashboard_items', 100))
        c.visual.admin_grid_items = safe_int(rc_config.get('rhodecode_admin_grid_items', 100))
        c.visual.repository_fields = str2bool(rc_config.get('rhodecode_repository_fields'))
        c.visual.show_version = str2bool(rc_config.get('rhodecode_show_version'))
        c.visual.use_gravatar = str2bool(rc_config.get('rhodecode_use_gravatar'))
        c.visual.gravatar_url = rc_config.get('rhodecode_gravatar_url')

        c.ga_code = rc_config.get('rhodecode_ga_code')
        c.rhodecode_name = rc_config.get('rhodecode_title')
        c.clone_uri_tmpl = rc_config.get('rhodecode_clone_uri_tmpl')

        ## INI stored
        c.visual.allow_repo_location_change = str2bool(config.get('allow_repo_location_change', True))
        c.visual.allow_custom_hooks_settings = str2bool(config.get('allow_custom_hooks_settings', True))

        c.rhodecode_instanceid = config.get('instance_id')
        c.issues_url = config.get('bugtracker', url('issues_url'))
        # END CONFIG VARS

        c.repo_name = get_repo_slug(request)  # can be empty
        c.backends = BACKENDS.keys()
        c.unread_notifications = NotificationModel()\
                        .get_unread_cnt_for_user(c.rhodecode_user.user_id)

        self.cut_off_limit = safe_int(config.get('cut_off_limit'))
        self.sa = meta.Session
        self.scm_model = ScmModel(self.sa)

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        try:
            self.ip_addr = _get_ip_addr(environ)
            # make sure that we update permissions each time we call controller
            api_key = request.GET.get('api_key')

            if api_key:
                # when using API_KEY we are sure user exists.
                auth_user = AuthUser(api_key=api_key, ip_addr=self.ip_addr)
                authenticated = False
            else:
                cookie_store = CookieStoreWrapper(session.get('rhodecode_user'))
                try:
                    auth_user = AuthUser(user_id=cookie_store.get('user_id', None),
                                         ip_addr=self.ip_addr)
                except UserCreationError, e:
                    from kallithea.lib import helpers as h
                    h.flash(e, 'error')
                    # container auth or other auth functions that create users on
                    # the fly can throw this exception signaling that there's issue
                    # with user creation, explanation should be provided in
                    # Exception itself
                    auth_user = AuthUser(ip_addr=self.ip_addr)

                authenticated = cookie_store.get('is_authenticated')

            if not auth_user.is_authenticated and auth_user.user_id is not None:
                # user is not authenticated and not empty
                auth_user.set_authenticated(authenticated)
            request.user = auth_user
            #set globals for auth user
            self.rhodecode_user = c.rhodecode_user = auth_user
            log.info('IP: %s User: %s accessed %s' % (
               self.ip_addr, auth_user, safe_unicode(_get_access_path(environ)))
            )
            return WSGIController.__call__(self, environ, start_response)
        finally:
            meta.Session.remove()


class BaseRepoController(BaseController):
    """
    Base class for controllers responsible for loading all needed data for
    repository loaded items are

    c.rhodecode_repo: instance of scm repository
    c.db_repo: instance of db
    c.repository_followers: number of followers
    c.repository_forks: number of forks
    c.repository_following: weather the current user is following the current repo
    """

    def __before__(self):
        super(BaseRepoController, self).__before__()
        if c.repo_name:  # extracted from routes
            _dbr = Repository.get_by_repo_name(c.repo_name)
            if not _dbr:
                return

            log.debug('Found repository in database %s with state `%s`'
                      % (safe_unicode(_dbr), safe_unicode(_dbr.repo_state)))
            route = getattr(request.environ.get('routes.route'), 'name', '')

            # allow to delete repos that are somehow damages in filesystem
            if route in ['delete_repo']:
                return

            if _dbr.repo_state in [Repository.STATE_PENDING]:
                if route in ['repo_creating_home']:
                    return
                check_url = url('repo_creating_home', repo_name=c.repo_name)
                return redirect(check_url)

            dbr = c.db_repo = _dbr
            c.rhodecode_repo = c.db_repo.scm_instance
            if c.rhodecode_repo is None:
                log.error('%s this repository is present in database but it '
                          'cannot be created as an scm instance', c.repo_name)

                redirect(url('home'))

            # update last change according to VCS data
            dbr.update_changeset_cache(dbr.get_changeset())

            # some globals counter for menu
            c.repository_followers = self.scm_model.get_followers(dbr)
            c.repository_forks = self.scm_model.get_forks(dbr)
            c.repository_pull_requests = self.scm_model.get_pull_requests(dbr)
            c.repository_following = self.scm_model.is_following_repo(
                                    c.repo_name, self.rhodecode_user.user_id)
