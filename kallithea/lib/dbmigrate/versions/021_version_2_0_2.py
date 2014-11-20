import os
import logging
import datetime

from sqlalchemy import *

from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *

from kallithea.model import meta
from kallithea.lib.dbmigrate.versions import _reset_base, notify

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    """
    Upgrade operations go here.
    Don't create your own engine; bind migrate_engine to your metadata
    """
    _reset_base(migrate_engine)
    from kallithea.lib.dbmigrate.schema import db_2_0_1
    tbl = db_2_0_1.RepoGroup.__table__

    created_on = Column('created_on', DateTime(timezone=False), nullable=True,
                        default=datetime.datetime.now)
    created_on.create(table=tbl)

    #fix null values on certain columns when upgrading from older releases
    tbl = db_2_0_1.UserLog.__table__
    col = tbl.columns.user_id
    col.alter(nullable=True)

    tbl = db_2_0_1.UserFollowing.__table__
    col = tbl.columns.follows_repository_id
    col.alter(nullable=True)

    tbl = db_2_0_1.UserFollowing.__table__
    col = tbl.columns.follows_user_id
    col.alter(nullable=True)

    # issue fixups
    fixups(db_2_0_1, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    notify('Fixing default created on for repo groups')

    for gr in models.RepoGroup.get_all():
        gr.created_on = datetime.datetime.now()
        _SESSION().add(gr)
        _SESSION().commit()

    repo_store_path = models.Ui.get_repos_location()
    _store = os.path.join(repo_store_path, '.cache', 'largefiles')
    notify('Setting largefiles usercache')
    print _store

    if not models.Ui.get_by_key('usercache'):
        largefiles = models.Ui()
        largefiles.ui_section = 'largefiles'
        largefiles.ui_key = 'usercache'
        largefiles.ui_value = _store
        _SESSION().add(largefiles)
        _SESSION().commit()
