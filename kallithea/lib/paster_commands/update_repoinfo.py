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
kallithea.lib.paster_commands.make_rcextensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

uodate-repoinfo paster command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Jul 14, 2012
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from __future__ import with_statement

import os
import sys
import logging
import string

from kallithea.lib.utils import BasePasterCommand
from kallithea.model.db import Repository
from kallithea.model.repo import RepoModel
from kallithea.model.meta import Session

# Add location of top level folder to sys.path
from os.path import dirname as dn
rc_path = dn(dn(dn(os.path.realpath(__file__))))
sys.path.append(rc_path)

log = logging.getLogger(__name__)


class Command(BasePasterCommand):

    max_args = 1
    min_args = 1

    usage = "CONFIG_FILE"
    group_name = "Kallithea"
    takes_config_file = -1
    parser = BasePasterCommand.standard_parser(verbose=True)
    summary = "Updates repositories caches for last changeset"

    def command(self):
        #get SqlAlchemy session
        self._init_session()

        repo_update_list = map(string.strip,
                               self.options.repo_update_list.split(',')) \
                               if self.options.repo_update_list else None

        if repo_update_list:
            repo_list = Repository.query()\
                .filter(Repository.repo_name.in_(repo_update_list))
        else:
            repo_list = Repository.getAll()
        RepoModel.update_repoinfo(repositories=repo_list)
        Session().commit()

        if self.options.invalidate_cache:
            for r in repo_list:
                r.set_invalidate()
        log.info('Updated cache for %s repositories' % (len(repo_list)))

    def update_parser(self):
        self.parser.add_option('--update-only',
                           action='store',
                           dest='repo_update_list',
                           help="Specifies a comma separated list of repositores "
                                "to update last commit info for. OPTIONAL")
        self.parser.add_option('--invalidate-cache',
                           action='store_true',
                           dest='invalidate_cache',
                           help="Trigger cache invalidation event for repos. "
                                "OPTIONAL")
