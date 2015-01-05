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
SQLAlchemy Metadata and Session object
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from beaker import cache

from kallithea.lib import caching_query


# Beaker CacheManager.  A home base for cache configurations.
cache_manager = cache.CacheManager()

__all__ = ['Base', 'Session']

#
# SQLAlchemy session manager.
#
session_factory = sessionmaker(
    query_cls=caching_query.query_callable(cache_manager),
    expire_on_commit=True)
Session = scoped_session(session_factory)

# The base class for declarative schemas in db.py
# Engine is injected when model.__init__.init_model() sets meta.Base.metadata.bind
Base = declarative_base()

#to use cache use this in query
#.options(FromCache("sqlalchemy_cache_type", "cachekey"))
