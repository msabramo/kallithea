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
kallithea.controllers.login
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Login controller for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Apr 22, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import formencode
import datetime
import urlparse

from formencode import htmlfill
from webob.exc import HTTPFound
from pylons.i18n.translation import _
from pylons.controllers.util import redirect
from pylons import request, session, tmpl_context as c, url

import kallithea.lib.helpers as h
from kallithea.lib.auth import AuthUser, HasPermissionAnyDecorator
from kallithea.lib.auth_modules import importplugin
from kallithea.lib.base import BaseController, render
from kallithea.lib.exceptions import UserCreationError
from kallithea.model.db import User, Setting
from kallithea.model.forms import LoginForm, RegisterForm, PasswordResetForm
from kallithea.model.user import UserModel
from kallithea.model.meta import Session


log = logging.getLogger(__name__)


class LoginController(BaseController):

    def __before__(self):
        super(LoginController, self).__before__()

    def _store_user_in_session(self, username, remember=False):
        user = User.get_by_username(username, case_insensitive=True)
        auth_user = AuthUser(user.user_id)
        auth_user.set_authenticated()
        cs = auth_user.get_cookie_store()
        session['authuser'] = cs
        user.update_lastlogin()
        Session().commit()

        # If they want to be remembered, update the cookie
        if remember:
            _year = (datetime.datetime.now() +
                     datetime.timedelta(seconds=60 * 60 * 24 * 365))
            session._set_cookie_expires(_year)

        session.save()

        log.info('user %s is now authenticated and stored in '
                 'session, session attrs %s' % (username, cs))

        # dumps session attrs back to cookie
        session._update_cookie_out()
        # we set new cookie
        headers = None
        if session.request['set_cookie']:
            # send set-cookie headers back to response to update cookie
            headers = [('Set-Cookie', session.request['cookie_out'])]
        return headers

    def _validate_came_from(self, came_from):
        if not came_from:
            return came_from

        parsed = urlparse.urlparse(came_from)
        server_parsed = urlparse.urlparse(url.current())
        allowed_schemes = ['http', 'https']
        if parsed.scheme and parsed.scheme not in allowed_schemes:
            log.error('Suspicious URL scheme detected %s for url %s' %
                     (parsed.scheme, parsed))
            came_from = url('home')
        elif server_parsed.netloc != parsed.netloc:
            log.error('Suspicious NETLOC detected %s for url %s server url '
                      'is: %s' % (parsed.netloc, parsed, server_parsed))
            came_from = url('home')
        return came_from

    def index(self):
        _default_came_from = url('home')
        came_from = self._validate_came_from(request.GET.get('came_from'))
        c.came_from = came_from or _default_came_from

        not_default = self.authuser.username != User.DEFAULT_USER
        ip_allowed = self.authuser.ip_allowed

        # redirect if already logged in
        if self.authuser.is_authenticated and not_default and ip_allowed:
            raise HTTPFound(location=c.came_from)

        if request.POST:
            # import Login Form validator class
            login_form = LoginForm()
            try:
                session.invalidate()
                c.form_result = login_form.to_python(dict(request.POST))
                # form checks for username/password, now we're authenticated
                headers = self._store_user_in_session(
                                        username=c.form_result['username'],
                                        remember=c.form_result['remember'])
                raise HTTPFound(location=c.came_from, headers=headers)
            except formencode.Invalid, errors:
                defaults = errors.value
                # remove password from filling in form again
                del defaults['password']
                return htmlfill.render(
                    render('/login.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8")
            except UserCreationError, e:
                # container auth or other auth functions that create users on
                # the fly can throw this exception signaling that there's issue
                # with user creation, explanation should be provided in
                # Exception itself
                h.flash(e, 'error')

        # check if we use container plugin, and try to login using it.
        auth_plugins = Setting.get_auth_plugins()
        if any((importplugin(name).is_container_auth for name in auth_plugins)):
            from kallithea.lib import auth_modules
            try:
                auth_info = auth_modules.authenticate('', '', request.environ)
            except UserCreationError, e:
                log.error(e)
                h.flash(e, 'error')
                # render login, with flash message about limit
                return render('/login.html')

            if auth_info:
                headers = self._store_user_in_session(auth_info.get('username'))
                raise HTTPFound(location=c.came_from, headers=headers)
        return render('/login.html')

    @HasPermissionAnyDecorator('hg.admin', 'hg.register.auto_activate',
                               'hg.register.manual_activate')
    def register(self):
        c.auto_active = 'hg.register.auto_activate' in User.get_default_user()\
            .AuthUser.permissions['global']

        settings = Setting.get_app_settings()
        captcha_private_key = settings.get('captcha_private_key')
        c.captcha_active = bool(captcha_private_key)
        c.captcha_public_key = settings.get('captcha_public_key')

        if request.POST:
            register_form = RegisterForm()()
            try:
                form_result = register_form.to_python(dict(request.POST))
                form_result['active'] = c.auto_active

                if c.captcha_active:
                    from kallithea.lib.recaptcha import submit
                    response = submit(request.POST.get('recaptcha_challenge_field'),
                                      request.POST.get('recaptcha_response_field'),
                                      private_key=captcha_private_key,
                                      remoteip=self.ip_addr)
                    if c.captcha_active and not response.is_valid:
                        _value = form_result
                        _msg = _('bad captcha')
                        error_dict = {'recaptcha_field': _msg}
                        raise formencode.Invalid(_msg, _value, None,
                                                 error_dict=error_dict)

                UserModel().create_registration(form_result)
                h.flash(_('You have successfully registered into Kallithea'),
                        category='success')
                Session().commit()
                return redirect(url('login_home'))

            except formencode.Invalid, errors:
                return htmlfill.render(
                    render('/register.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8")
            except UserCreationError, e:
                # container auth or other auth functions that create users on
                # the fly can throw this exception signaling that there's issue
                # with user creation, explanation should be provided in
                # Exception itself
                h.flash(e, 'error')

        return render('/register.html')

    def password_reset(self):
        settings = Setting.get_app_settings()
        captcha_private_key = settings.get('captcha_private_key')
        c.captcha_active = bool(captcha_private_key)
        c.captcha_public_key = settings.get('captcha_public_key')

        if request.POST:
            password_reset_form = PasswordResetForm()()
            try:
                form_result = password_reset_form.to_python(dict(request.POST))
                if c.captcha_active:
                    from kallithea.lib.recaptcha import submit
                    response = submit(request.POST.get('recaptcha_challenge_field'),
                                      request.POST.get('recaptcha_response_field'),
                                      private_key=captcha_private_key,
                                      remoteip=self.ip_addr)
                    if c.captcha_active and not response.is_valid:
                        _value = form_result
                        _msg = _('bad captcha')
                        error_dict = {'recaptcha_field': _msg}
                        raise formencode.Invalid(_msg, _value, None,
                                                 error_dict=error_dict)
                UserModel().reset_password_link(form_result)
                h.flash(_('Your password reset link was sent'),
                            category='success')
                return redirect(url('login_home'))

            except formencode.Invalid, errors:
                return htmlfill.render(
                    render('/password_reset.html'),
                    defaults=errors.value,
                    errors=errors.error_dict or {},
                    prefix_error=False,
                    encoding="UTF-8")

        return render('/password_reset.html')

    def password_reset_confirmation(self):
        if request.GET and request.GET.get('key'):
            try:
                user = User.get_by_api_key(request.GET.get('key'))
                data = dict(email=user.email)
                UserModel().reset_password(data)
                h.flash(_('Your password reset was successful, '
                          'new password has been sent to your email'),
                            category='success')
            except Exception, e:
                log.error(e)
                return redirect(url('reset_password'))

        return redirect(url('login_home'))

    def logout(self):
        session.delete()
        log.info('Logging out and deleting session for user')
        redirect(url('home'))
