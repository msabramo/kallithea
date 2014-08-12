#!/usr/bin/env python

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
Script for rebranding of database to and from what Kallithea expects

Works on databases from v1.7.2 to v2.2.5
"""

import sys
from sqlalchemy import *
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import migrate.changeset # a part of sqlalchemy-migrate which is available on pypi

def do_migrate(db, old, new):
    print 'Migrating %s from %s to %s' % (db, old or '?', new)
    metadata = MetaData()
    metadata.bind = create_engine(db)
    metadata.reflect()
    assert metadata.tables, 'Cannot reflect table names from db'

    if not old:
        assert 'db_migrate_version' in metadata.tables, 'Cannot reflect db_migrate_version from db'
        t = metadata.tables['db_migrate_version']
        l = t.select().where(t.c.repository_path == 'versions').execute().fetchall()
        assert len(l) == 1, 'Cannot find a single versions entry in db_migrate_version'
        assert l[0].repository_id.endswith('_db_migrations')
        old = l[0].repository_id[:-len('_db_migrations')]
        print 'Detected migration from old name %s' % old
        if new != old:
            assert not t.select().where(t.c.repository_id == new + '_db_migrations').execute().fetchall(), 'db_migrate_version has entries for both old and new name'

    def tablename(brand, s):
        return s if brand == 'kallithea' else (brand + '_' + s)
    new_ui_name = tablename(new, 'ui')
    old_ui_name = tablename(old, 'ui')
    new_settings_name = tablename(new, 'settings')
    old_settings_name = tablename(old, 'settings')

    # Table renames using sqlalchemy-migrate (available on pypi)
    if new_ui_name == old_ui_name:
        print 'No renaming of %s' % new_ui_name
    else:
        try:
            t = metadata.tables[old_ui_name]
            print 'Renaming', t, 'to', new_ui_name
            migrate.changeset.rename_table(t, new_ui_name)
        except KeyError, e:
            print 'Not renaming ui:', e

    if new_settings_name == old_settings_name:
        print 'No renaming of %s' % new_settings_name
    else:
        try:
            t = metadata.tables[old_settings_name]
            print 'Renaming', t, 'to', new_settings_name
            migrate.changeset.rename_table(t, new_settings_name)
        except KeyError, e:
            print 'Not renaming settings:', e

    # using this API because ... dunno ... it is simple and works
    conn = metadata.bind.connect()
    trans = conn.begin()
    t = metadata.tables['users']

    print 'Bulk fixing of User extern_name'
    try:
        t.c.extern_name
    except AttributeError:
        print 'No extern_name to rename'
    else:
        t.update().where(t.c.extern_name == old).values(extern_name=new).execute()

    print 'Bulk fixing of User extern_type'
    try:
        t.c.extern_type
    except AttributeError:
        print 'No extern_type to rename'
    else:
        t.update().where(t.c.extern_type == old).values(extern_type=new).execute()

    trans.commit()

    # For the following conversions, use ORM ... and create stub models that works for that purpose
    Base = sqlalchemy.ext.declarative.declarative_base()

    class Ui(Base):
        __tablename__ = new_ui_name
        ui_id = Column("ui_id", Integer(), primary_key=True)
        ui_section = Column("ui_section", String())
        ui_key = Column("ui_key", String())
        ui_value = Column("ui_value", String())
        ui_active = Column("ui_active", Boolean())

    class Setting(Base):
        __tablename__ = new_settings_name
        app_settings_id = Column("app_settings_id", Integer(), primary_key=True)
        app_settings_name = Column("app_settings_name", String())
        app_settings_value = Column("app_settings_value", String())
        #app_settings_type = Column("app_settings_type", String()) # not present in v1.7.2

    class DbMigrateVersion(Base):
        __tablename__ = 'db_migrate_version'
        repository_id = Column('repository_id', String(), primary_key=True)
        repository_path = Column('repository_path', Text)
        version = Column('version', Integer)

    Session = sqlalchemy.orm.sessionmaker(bind=metadata.bind)
    session = Session()

    print 'Fixing hook names'

    oldhooks = u'python:%s.lib.hooks.' % old
    newhooks = u'python:%s.lib.hooks.' % new
    for u in session.query(Ui).filter(Ui.ui_section == 'hooks').all():
        if u.ui_value.startswith(oldhooks):
            print '- fixing %s' % u.ui_key
            u.ui_value = newhooks + u.ui_value[len(oldhooks):]
            session.add(u)
    session.commit()

    print 'Fixing auth module names'
    old_auth_name = 'internal' if old == 'kallithea' else old
    new_auth_name = 'internal' if new == 'kallithea' else new
    for s in session.query(Setting).filter(Setting.app_settings_name == 'auth_plugins').all():
        print '- fixing %s' % s.app_settings_name
        s.app_settings_value = (s.app_settings_value
                                .replace(old + '.lib.auth_modules.auth_', new + '.lib.auth_modules.auth_')
                                .replace('.auth_modules.auth_' + old_auth_name, '.auth_modules.auth_' + new_auth_name))
        session.add(s)
    for s in session.query(Setting).filter(Setting.app_settings_name == 'auth_' + old_auth_name + '_enabled').all():
        print '- fixing %s' % s.app_settings_name
        s.app_settings_name = 'auth_' + new_auth_name + '_enabled'
        session.add(s)
    session.commit()

    print 'Fixing db migration version number'
    for s in session.query(DbMigrateVersion).filter(DbMigrateVersion.repository_id == old + '_db_migrations', DbMigrateVersion.repository_path == 'versions').all():
        print '- fixing %s' % s.repository_id
        s.repository_id = new + '_db_migrations'
    session.commit()

    print 'Done'

def main(argv):
    if len(argv) < 2 or argv[1] in ['-h', '--help']:
        print 'usage: kallithea/bin/rebranddb.py DBSTRING [NEW] [OLD]'
        print '  where DBSTRING is the value of sqlalchemy.db1.url from the .ini,'
        print '  NEW defaults to "kallithea", OLD is by default detected from the db"'
        raise SystemExit(0)
    new = 'kallithea'
    if len(argv) > 2:
        new = argv[2]
    old = None
    if len(argv) > 3:
        old = argv[3]
    do_migrate(argv[1], old, new)

if __name__ == '__main__':
    main(sys.argv)
