import logging

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
    from kallithea.lib.dbmigrate.schema import db_1_6_0

    #==========================================================================
    # USER LOGS
    #==========================================================================
    tbl = db_1_6_0.RepositoryField.__table__
    tbl.create()

    # issue fixups
    fixups(db_1_6_0, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    notify('Upgrading repositories Caches')
    repositories = models.Repository.getAll()
    for repo in repositories:
        print repo
        repo.update_changeset_cache()
        _SESSION().commit()
