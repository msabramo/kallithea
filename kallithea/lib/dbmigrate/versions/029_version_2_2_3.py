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
    from kallithea.lib.dbmigrate.schema import db_2_2_0

    # issue fixups
    fixups(db_2_2_0, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    notify('Adding grid items options now...')

    settings = [
        ('admin_grid_items', 25, 'int'),  # old hardcoded value was 25
    ]

    for name, default, type_ in settings:
        setting = models.Setting.get_by_name(name)
        if not setting:
            # if we don't have this option create it
            setting = models.Setting(name, default, type_)
        setting._app_settings_type = type_
        _SESSION().add(setting)
        _SESSION().commit()
