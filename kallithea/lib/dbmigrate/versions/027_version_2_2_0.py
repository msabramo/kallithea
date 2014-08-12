import logging

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
    from kallithea.lib.dbmigrate.schema import db_2_2_0

    # issue fixups
    fixups(db_2_2_0, meta.Session)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine


def fixups(models, _SESSION):
    # ** create default permissions ** #
    #=====================================
    for p in models.Permission.PERMS:
        if not models.Permission.get_by_key(p[0]):
            new_perm = models.Permission()
            new_perm.permission_name = p[0]
            new_perm.permission_longname = p[0]  #translation err with p[1]
            print 'Creating new permission %s' % p[0]
            _SESSION().add(new_perm)

    _SESSION().commit()

    # ** set default create_on_write to active
    user = models.User.get_default_user()
    _def = 'hg.create.write_on_repogroup.true'
    new = models.UserToPerm()
    new.user = user
    new.permission = models.Permission.get_by_key(_def)
    print 'Setting default to %s' % _def
    _SESSION().add(new)
    _SESSION().commit()
