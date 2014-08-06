import logging

from sqlalchemy import *

from kallithea.lib.dbmigrate.migrate import *
from kallithea.lib.dbmigrate.migrate.changeset import *


log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    """ Upgrade operations go here.
    Don't create your own engine; bind migrate_engine to your metadata
    """
    #==========================================================================
    # Add table `users_group_repo_group_to_perm`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import UserGroupRepoGroupToPerm
    UserGroupRepoGroupToPerm().__table__.create()

    #==========================================================================
    # Add table `changeset_comments`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import  ChangesetComment
    ChangesetComment().__table__.create()

    #==========================================================================
    # Add table `notifications`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import  Notification
    Notification().__table__.create()

    #==========================================================================
    # Add table `user_to_notification`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import  UserNotification
    UserNotification().__table__.create()

    #==========================================================================
    # Add unique to table `users_group_to_perm`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import UserGroupToPerm
    tbl = UserGroupToPerm().__table__
    cons = UniqueConstraint('users_group_id', 'permission_id', table=tbl)
    cons.create()

    #==========================================================================
    # Fix unique constrain on table `user_logs`
    #==========================================================================
    from kallithea.lib.dbmigrate.schema.db_1_3_0 import UserLog
    tbl = UserLog().__table__
    col = Column("repository_id", Integer(), ForeignKey('repositories.repo_id'),
                 nullable=False, unique=None, default=None)
    col.alter(nullable=True, table=tbl)

    #==========================================================================
    # Rename table `group_to_perm` to `user_repo_group_to_perm`
    #==========================================================================
    tbl = Table('group_to_perm', MetaData(bind=migrate_engine), autoload=True,
                    autoload_with=migrate_engine)
    tbl.rename('user_repo_group_to_perm')

    return


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
