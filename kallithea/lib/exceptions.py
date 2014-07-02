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
kallithea.lib.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~

Set of custom exceptions used in Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 17, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from webob.exc import HTTPClientError


class LdapUsernameError(Exception):
    pass


class LdapPasswordError(Exception):
    pass


class LdapConnectionError(Exception):
    pass


class LdapImportError(Exception):
    pass


class DefaultUserException(Exception):
    pass


class UserOwnsReposException(Exception):
    pass


class UserGroupsAssignedException(Exception):
    pass


class StatusChangeOnClosedPullRequestError(Exception):
    pass


class AttachedForksError(Exception):
    pass


class RepoGroupAssignmentError(Exception):
    pass


class NonRelativePathError(Exception):
    pass


class HTTPLockedRC(HTTPClientError):
    """
    Special Exception For locked Repos in Kallithea, the return code can
    be overwritten by _code keyword argument passed into constructors
    """
    code = 423
    title = explanation = 'Repository Locked'

    def __init__(self, reponame, username, *args, **kwargs):
        from kallithea import CONFIG
        from kallithea.lib.utils2 import safe_int
        _code = CONFIG.get('lock_ret_code')
        self.code = safe_int(_code, self.code)
        self.title = self.explanation = ('Repository `%s` locked by '
                                         'user `%s`' % (reponame, username))
        super(HTTPLockedRC, self).__init__(*args, **kwargs)


class IMCCommitError(Exception):
    pass


class UserCreationError(Exception):
    pass


class RepositoryCreationError(Exception):
    pass


class HgsubversionImportError(Exception):
    pass
