import logging

from sqlalchemy import *

from kallithea import EXTERN_TYPE_INTERNAL
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
    from kallithea.lib.dbmigrate.schema import db_2_0_1

    # issue fixups
    fixups(db_2_0_1, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    #fix all empty extern type users to default 'internal'
    for usr in models.User.query().all():
        if not usr.extern_name:
            usr.extern_name = EXTERN_TYPE_INTERNAL
            usr.extern_type = EXTERN_TYPE_INTERNAL
            _SESSION().add(usr)
            _SESSION().commit()
