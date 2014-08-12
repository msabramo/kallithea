import logging
import datetime

from sqlalchemy import *

from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *


log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    """ Upgrade operations go here.
    Don't create your own engine; bind migrate_engine to your metadata
    """

    #==========================================================================
    # Add table `groups``
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import Group as Group
    Group().__table__.create()

    #==========================================================================
    # Add table `group_to_perm`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import UserRepoGroupToPerm
    UserRepoGroupToPerm().__table__.create()

    #==========================================================================
    # Add table `users_groups`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import UserGroup
    UserGroup().__table__.create()

    #==========================================================================
    # Add table `users_groups_members`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import UserGroupMember
    UserGroupMember().__table__.create()

    #==========================================================================
    # Add table `users_group_repo_to_perm`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import UserGroupRepoToPerm
    UserGroupRepoToPerm().__table__.create()

    #==========================================================================
    # Add table `users_group_to_perm`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import UserGroupToPerm
    UserGroupToPerm().__table__.create()

    #==========================================================================
    # Upgrade of `users` table
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import User

    #add column
    ldap_dn = Column("ldap_dn", String(length=255, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    ldap_dn.create(User().__table__)

    api_key = Column("api_key", String(length=255, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    api_key.create(User().__table__)

    #remove old column
    is_ldap = Column("is_ldap", Boolean(), nullable=False, unique=None, default=False)
    is_ldap.drop(User().__table__)

    #==========================================================================
    # Upgrade of `repositories` table
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_2_0 import Repository

    #ADD clone_uri column#

    clone_uri = Column("clone_uri", String(length=255, convert_unicode=False,
                                           assert_unicode=None),
                        nullable=True, unique=False, default=None)

    clone_uri.create(Repository().__table__)

    #ADD downloads column#
    enable_downloads = Column("downloads", Boolean(), nullable=True, unique=None, default=True)
    enable_downloads.create(Repository().__table__)

    #ADD column created_on
    created_on = Column('created_on', DateTime(timezone=False), nullable=True,
                        unique=None, default=datetime.datetime.now)
    created_on.create(Repository().__table__)

    #ADD group_id column#
    group_id = Column("group_id", Integer(), ForeignKey('groups.group_id'),
                  nullable=True, unique=False, default=None)

    group_id.create(Repository().__table__)

    #==========================================================================
    # Upgrade of `user_followings` table
    #==========================================================================

    from kallithea.lib.dbmigrate.schema.db_1_2_0 import UserFollowing

    follows_from = Column('follows_from', DateTime(timezone=False),
                          nullable=True, unique=None,
                          default=datetime.datetime.now)
    follows_from.create(UserFollowing().__table__)

    return


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
