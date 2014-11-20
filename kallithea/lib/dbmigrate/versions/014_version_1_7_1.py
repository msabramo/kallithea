import logging
import datetime

from sqlalchemy import *

from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *

from kallithea.model import meta
from kallithea.lib.dbmigrate.versions import _reset_base

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    """
    Upgrade operations go here.
    Don't create your own engine; bind migrate_engine to your metadata
    """
    _reset_base(migrate_engine)
    from kallithea.lib.dbmigrate.schema import db_1_7_0

    #==========================================================================
    # Gist
    #==========================================================================
    tbl = db_1_7_0.Gist.__table__
    user_id = tbl.columns.gist_expires
    user_id.alter(type=Float(53))

    # issue fixups
    fixups(db_1_7_0, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    # fix nullable columns on last_update
    for r in models.Repository().get_all():
        if r.updated_on is None:
            r.updated_on = datetime.datetime.fromtimestamp(0)
            _SESSION().add(r)
    _SESSION().commit()
