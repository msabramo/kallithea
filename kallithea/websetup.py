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
kallithea.websetup
~~~~~~~~~~~~~~~~~~

Weboperations and setup for kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Dec 11, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

import logging

from kallithea.config.environment import load_environment
from kallithea.lib.db_manage import DbManage
from kallithea.model.meta import Session


log = logging.getLogger(__name__)


def setup_app(command, conf, vars):
    """Place any commands to setup kallithea here"""
    dbconf = conf['sqlalchemy.db1.url']
    dbmanage = DbManage(log_sql=True, dbconf=dbconf, root=conf['here'],
                        tests=False, cli_args=command.options.__dict__)
    dbmanage.create_tables(override=True)
    dbmanage.set_db_version()
    opts = dbmanage.config_prompt(None)
    dbmanage.create_settings(opts)
    dbmanage.create_default_user()
    dbmanage.admin_prompt()
    dbmanage.create_permissions()
    dbmanage.populate_default_permissions()
    Session().commit()
    load_environment(conf.global_conf, conf.local_conf, initial=True)
    DbManage.check_waitress()
