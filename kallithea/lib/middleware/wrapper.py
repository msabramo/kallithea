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
kallithea.lib.middleware.wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

request time measuring app

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: May 23, 2013
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import time
import logging
from kallithea.lib.base import _get_ip_addr, _get_access_path
from kallithea.lib.utils2 import safe_unicode


class RequestWrapper(object):

    def __init__(self, app, config):
        self.application = app
        self.config = config

    def __call__(self, environ, start_response):
        start = time.time()
        try:
            return self.application(environ, start_response)
        finally:
            log = logging.getLogger('kallithea.' + self.__class__.__name__)
            log.info('IP: %s Request to %s time: %.3fs' % (
                _get_ip_addr(environ),
                safe_unicode(_get_access_path(environ)), time.time() - start)
            )
