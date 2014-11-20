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
    from kallithea.lib.dbmigrate.schema import db_1_8_0
    tbl = db_1_8_0.Setting.__table__
    app_settings_type = Column("app_settings_type",
                               String(255, convert_unicode=False, assert_unicode=None),
                               nullable=True, unique=None, default=None)
    app_settings_type.create(table=tbl)

    # issue fixups
    fixups(db_1_8_0, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    notify('Fixing default options now...')

    settings = [
        #general
        ('realm', '', 'unicode'),
        ('title', '', 'unicode'),
        ('ga_code', '', 'unicode'),
        ('show_public_icon', False, 'bool'),
        ('show_private_icon', True, 'bool'),
        ('stylify_metatags', True, 'bool'),

        # defaults
        ('default_repo_enable_locking',  False, 'bool'),
        ('default_repo_enable_downloads', False, 'bool'),
        ('default_repo_enable_statistics', False, 'bool'),
        ('default_repo_private', False, 'bool'),
        ('default_repo_type', 'hg', 'unicode'),

        #other
        ('dashboard_items', 100, 'int'),
        ('show_version', True, 'bool')
    ]

    for name, default, type_ in settings:
        setting = models.Setting.get_by_name(name)
        if not setting:
            # if we don't have this option create it
            setting = models.Setting(name, default, type_)

        # fix certain key to new defaults
        if name in ['title', 'show_public_icon']:
            # change title if it's only the default
            if name == 'title' and setting.app_settings_value == 'Kallithea':
                setting.app_settings_value = default
            else:
                setting.app_settings_value = default

        setting._app_settings_type = type_
        _SESSION().add(setting)
        _SESSION().commit()
