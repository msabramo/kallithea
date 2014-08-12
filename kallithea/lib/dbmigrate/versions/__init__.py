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
kallithea.lib.dbmigrate.versions.__init__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Package containing new versions of database models

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Dec 11, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *

from kallithea.model import meta


def notify(msg, caps=True):
    """
    Notification for migrations messages
    """
    ml = len(msg) + (4 * 2)
    formatted_msg = ('\n%s\n*** %s ***\n%s' % ('*' * ml, msg, '*' * ml))
    if caps:
        formatted_msg = formatted_msg.upper()
    print(formatted_msg)


def _reset_base(migrate_engine):
    ## RESET COMPLETLY THE metadata for sqlalchemy to use previous declared Base
    Base = declarative_base()
    Base.metadata.clear()
    Base.metadata = MetaData()
    Base.metadata.bind = migrate_engine

    # new session and base
    #meta.Session = scoped_session(sessionmaker(expire_on_commit=True,))
    #meta.Session.configure(bind=migrate_engine)
    meta.Base = Base

    notify('SQLA BASE RESET !')
