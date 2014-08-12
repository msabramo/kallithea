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
kallithea.lib.paster_commands.make_index
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

make-index paster command for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Aug 17, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.

"""

from __future__ import with_statement

import os
import sys
import logging

from string import strip
from kallithea.model.repo import RepoModel
from kallithea.lib.utils import BasePasterCommand, load_rcextensions

# Add location of top level folder to sys.path
from os.path import dirname as dn
rc_path = dn(dn(dn(os.path.realpath(__file__))))
sys.path.append(rc_path)


class Command(BasePasterCommand):

    max_args = 1
    min_args = 1

    usage = "CONFIG_FILE"
    group_name = "Kallithea"
    takes_config_file = -1
    parser = BasePasterCommand.standard_parser(verbose=True)
    summary = "Creates or updates full text search index"

    def command(self):
        logging.config.fileConfig(self.path_to_ini_file)
        #get SqlAlchemy session
        self._init_session()
        from pylons import config
        index_location = config['index_dir']
        load_rcextensions(config['here'])

        repo_location = self.options.repo_location \
            if self.options.repo_location else RepoModel().repos_path
        repo_list = map(strip, self.options.repo_list.split(',')) \
            if self.options.repo_list else None

        repo_update_list = map(strip, self.options.repo_update_list.split(',')) \
            if self.options.repo_update_list else None

        #======================================================================
        # WHOOSH DAEMON
        #======================================================================
        from kallithea.lib.pidlock import LockHeld, DaemonLock
        from kallithea.lib.indexers.daemon import WhooshIndexingDaemon
        try:
            l = DaemonLock(file_=os.path.join(dn(dn(index_location)),
                                              'make_index.lock'))
            WhooshIndexingDaemon(index_location=index_location,
                                 repo_location=repo_location,
                                 repo_list=repo_list,
                                 repo_update_list=repo_update_list)\
                .run(full_index=self.options.full_index)
            l.release()
        except LockHeld:
            sys.exit(1)

    def update_parser(self):
        self.parser.add_option('--repo-location',
                          action='store',
                          dest='repo_location',
                          help="Specifies repositories location to index OPTIONAL",
                          )
        self.parser.add_option('--index-only',
                          action='store',
                          dest='repo_list',
                          help="Specifies a comma separated list of repositores "
                                "to build index on. If not given all repositories "
                                "are scanned for indexing. OPTIONAL",
                          )
        self.parser.add_option('--update-only',
                          action='store',
                          dest='repo_update_list',
                          help="Specifies a comma separated list of repositores "
                                "to re-build index on. OPTIONAL",
                          )
        self.parser.add_option('-f',
                          action='store_true',
                          dest='full_index',
                          help="Specifies that index should be made full i.e"
                                " destroy old and build from scratch",
                          default=False)
