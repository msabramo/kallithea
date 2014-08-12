import logging
import datetime

from sqlalchemy import *

from kallithea import EXTERN_TYPE_INTERNAL
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
    from kallithea.lib.dbmigrate.schema import db_2_0_0
    tbl = db_2_0_0.User.__table__

    extern_type = Column("extern_type",
                         String(255, convert_unicode=False, assert_unicode=None),
                         nullable=True, unique=None, default=None)
    extern_type.create(table=tbl)

    extern_name = Column("extern_name", String(255, convert_unicode=False, assert_unicode=None),
                         nullable=True, unique=None, default=None)
    extern_name.create(table=tbl)

    created_on = Column('created_on', DateTime(timezone=False),
                        nullable=True, default=datetime.datetime.now)
    created_on.create(table=tbl)

    # issue fixups
    fixups(db_2_0_0, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    notify('Fixing default created on')

    for usr in models.User.get_all():
        usr.created_on = datetime.datetime.now()
        _SESSION().add(usr)
        _SESSION().commit()

    notify('Migrating LDAP attribute to extern')
    for usr in models.User.get_all():
        ldap_dn = usr.ldap_dn
        if ldap_dn:
            usr.extern_name = ldap_dn
            usr.extern_type = 'ldap'
        else:
            usr.extern_name = EXTERN_TYPE_INTERNAL
            usr.extern_type = EXTERN_TYPE_INTERNAL
        _SESSION().add(usr)
        _SESSION().commit()
