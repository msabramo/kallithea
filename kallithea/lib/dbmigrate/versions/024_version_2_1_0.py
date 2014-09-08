import logging

from sqlalchemy import *

from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *

from kallithea.model import meta
from kallithea.lib.dbmigrate.versions import _reset_base, notify

from kallithea.lib.utils2 import str2bool

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    """
    Upgrade operations go here.
    Don't create your own engine; bind migrate_engine to your metadata
    """
    _reset_base(migrate_engine)
    from kallithea.lib.dbmigrate.schema import db_2_1_0

    # issue fixups
    fixups(db_2_1_0, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    from pylons import config

    notify('migrating options from .ini file')
    use_gravatar = str2bool(config.get('use_gravatar'))
    print('Setting gravatar use to: %s' % use_gravatar)
    sett = models.Setting.create_or_update('use_gravatar',
                                                    use_gravatar, 'bool')
    _SESSION().add(sett)
    _SESSION.commit()
    #set the new format of gravatar URL
    gravatar_url = models.User.DEFAULT_GRAVATAR_URL
    if config.get('alternative_gravatar_url'):
        gravatar_url = config.get('alternative_gravatar_url')

    print('Setting gravatar url to:%s' % gravatar_url)
    sett = models.Setting.create_or_update('gravatar_url',
                                                    gravatar_url, 'unicode')
    _SESSION().add(sett)
    _SESSION.commit()

    #now create new changed value of clone_url
    clone_uri_tmpl = models.Repository.DEFAULT_CLONE_URI
    print('settings new clone url template to %s' % clone_uri_tmpl)

    sett = models.Setting.create_or_update('clone_uri_tmpl',
                                                    clone_uri_tmpl, 'unicode')
    _SESSION().add(sett)
    _SESSION.commit()
