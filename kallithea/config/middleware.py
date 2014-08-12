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
    Pylons middleware initialization
"""

from beaker.middleware import SessionMiddleware
from routes.middleware import RoutesMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from paste.gzipper import make_gzip_middleware

from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp

from kallithea.lib.middleware.simplehg import SimpleHg
from kallithea.lib.middleware.simplegit import SimpleGit
from kallithea.lib.middleware.https_fixup import HttpsFixup
from kallithea.config.environment import load_environment
from kallithea.lib.middleware.wrapper import RequestWrapper


def make_app(global_conf, full_stack=True, static_files=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether or not this application provides a full WSGI stack (by
        default, meaning it handles its own exceptions and errors).
        Disable full_stack when this application is "managed" by
        another WSGI middleware.

    ``app_conf``
        The application's local configuration. Normally specified in
        the [app:<name>] section of the Paste ini file (where <name>
        defaults to main).

    """
    # Configure the Pylons environment
    config = load_environment(global_conf, app_conf)

    # The Pylons WSGI app
    app = PylonsApp(config=config)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    app = SessionMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
    if asbool(config['pdebug']):
        from kallithea.lib.profiler import ProfilingMiddleware
        app = ProfilingMiddleware(app)

    if asbool(full_stack):

        from kallithea.lib.middleware.sentry import Sentry
        from kallithea.lib.middleware.errormator import Errormator
        if Errormator and asbool(config['app_conf'].get('errormator')):
            app = Errormator(app, config)
        elif Sentry:
            app = Sentry(app, config)

        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # we want our low level middleware to get to the request ASAP. We don't
        # need any pylons stack middleware in them
        app = SimpleHg(app, config)
        app = SimpleGit(app, config)
        app = RequestWrapper(app, config)
        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])

    #enable https redirets based on HTTP_X_URL_SCHEME set by proxy
    if any(asbool(config.get(x)) for x in ['https_fixup', 'force_ssl', 'use_htsts']):
        app = HttpsFixup(app, config)

    # Establish the Registry for this application
    app = RegistryManager(app)

    if asbool(static_files):
        # Serve static files
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, app])
        app = make_gzip_middleware(app, global_conf, compress_level=1)

    app.config = config

    return app
