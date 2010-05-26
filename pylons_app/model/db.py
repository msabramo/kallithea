from pylons_app.model.meta import Base
from sqlalchemy.orm import relation, backref
from sqlalchemy import *

class Users(Base): 
    __tablename__ = 'users'
    __table_args__ = {'useexisting':True}
    user_id = Column("user_id", INTEGER(), nullable=False, unique=True, default=None, primary_key=1)
    username = Column("username", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    password = Column("password", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    active = Column("active", BOOLEAN(), nullable=True, unique=None, default=None)
    admin = Column("admin", BOOLEAN(), nullable=True, unique=None, default=None)
    name = Column("name", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    lastname = Column("lastname", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    email = Column("email", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    last_login = Column("last_login", DATETIME(timezone=False), nullable=True, unique=None, default=None)
    
    user_log = relation('UserLogs')
      
class UserLogs(Base): 
    __tablename__ = 'user_logs'
    __table_args__ = {'useexisting':True}
    user_log_id = Column("id", INTEGER(), nullable=False, unique=True, default=None, primary_key=1)
    user_id = Column("user_id", INTEGER(), ForeignKey(u'users.user_id'), nullable=True, unique=None, default=None)
    repository = Column("repository", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    action = Column("action", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
    action_date = Column("action_date", DATETIME(timezone=False), nullable=True, unique=None, default=None)
    
    user = relation('Users')


class Permissions(Base):
    __tablename__ = 'permissions'
    __table_args__ = {'useexisting':True}
    permission_id = Column("id", INTEGER(), nullable=False, unique=True, default=None, primary_key=1)
    permission_name = Column("permission_name", TEXT(length=None, convert_unicode=False, assert_unicode=None), nullable=True, unique=None, default=None)
