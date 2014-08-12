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
    from kallithea.lib.dbmigrate.schema import db_2_2_3

    # issue fixups
    fixups(db_2_2_3, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    notify('Creating repository states')
    for repo in models.Repository.get_all():
        _state = models.Repository.STATE_CREATED
        print 'setting repo %s state to "%s"' % (repo, _state)
        repo.repo_state = _state
        _SESSION().add(repo)
        _SESSION().commit()
