import sqlalchemy
from sqlalchemy.dialects import postgresql as sqlalchemy_psql

from rangeseeker.model import Strategy
from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.store.entity_repository import EntityRepository

metadata = sqlalchemy.MetaData()


UsersTable = sqlalchemy.Table(
    'tbl_users',
    metadata,
    sqlalchemy.Column(key='userId', name='id', type_=sqlalchemy_psql.UUID, primary_key=True),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='username', name='username', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.UniqueConstraint('username', name='tbl_users_ux_username'),
)

UsersRepository = EntityRepository(table=UsersTable, modelClass=User)


UserWalletsTable = sqlalchemy.Table(
    'tbl_user_wallets',
    metadata,
    sqlalchemy.Column(key='userWalletId', name='id', type_=sqlalchemy_psql.UUID, primary_key=True),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='userId', name='user_id', type_=sqlalchemy_psql.UUID, nullable=False),
    sqlalchemy.Column(key='walletAddress', name='wallet_address', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.UniqueConstraint('walletAddress', name='tbl_user_wallets_ux_wallet_address'),
)

UserWalletsRepository = EntityRepository(table=UserWalletsTable, modelClass=UserWallet)


StrategiesTable = sqlalchemy.Table(
    'tbl_strategies',
    metadata,
    sqlalchemy.Column(key='strategyId', name='id', type_=sqlalchemy_psql.UUID, primary_key=True),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='userId', name='user_id', type_=sqlalchemy_psql.UUID, nullable=False),
    sqlalchemy.Column(key='name', name='name', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='description', name='description', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='rulesJson', name='rules_json', type_=sqlalchemy_psql.JSONB, nullable=False),
    sqlalchemy.Column(key='feedRequirements', name='feed_requirements', type_=sqlalchemy_psql.ARRAY(sqlalchemy.Text), nullable=False),
    sqlalchemy.Column(key='summary', name='summary', type_=sqlalchemy.Text, nullable=False),
)

StrategiesRepository = EntityRepository(table=StrategiesTable, modelClass=Strategy)
