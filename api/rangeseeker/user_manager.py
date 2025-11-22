from core.exceptions import BadRequestException
from core.store.database import Database
from core.store.retriever import StringFieldFilter

from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.store import schema
from rangeseeker.store.entity_repository import UUIDFieldFilter


class UserManager:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_user(self, userId: str) -> User:
        return await schema.UsersRepository.get_one(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.UsersTable.c.userId.key, eq=userId)],
        )

    async def get_user_by_wallet_address(self, walletAddress: str) -> User:
        userWallet = await schema.UserWalletsRepository.get_one(
            database=self.database,
            fieldFilters=[StringFieldFilter(fieldName=schema.UserWalletsTable.c.walletAddress.key, eq=walletAddress)],
        )
        return await self.get_user(userId=userWallet.userId)

    async def get_user_by_username(self, username: str) -> User:
        return await schema.UsersRepository.get_one(
            database=self.database,
            fieldFilters=[StringFieldFilter(fieldName=schema.UsersTable.c.username.key, eq=username.lower())],
        )

    async def create_user(self, walletAddress: str, username: str) -> User:
        existingUserWallet = await schema.UserWalletsRepository.get_first(
            database=self.database,
            fieldFilters=[StringFieldFilter(fieldName=schema.UserWalletsTable.c.walletAddress.key, eq=walletAddress)],
        )
        if existingUserWallet:
            raise BadRequestException(message='USER_WALLET_EXISTS')
        existingUser = await schema.UsersRepository.get_first(
            database=self.database,
            fieldFilters=[StringFieldFilter(fieldName=schema.UsersTable.c.username.key, eq=username.lower())],
        )
        if existingUser:
            raise BadRequestException(message='USERNAME_EXISTS')
        user = await schema.UsersRepository.create(
            database=self.database,
            username=username.lower(),
        )
        await schema.UserWalletsRepository.create(
            database=self.database,
            userId=user.userId,
            walletAddress=walletAddress,
        )
        return user

    async def get_user_wallet(self, userId: str) -> UserWallet:
        return await schema.UserWalletsRepository.get_one(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.UserWalletsTable.c.userId.key, eq=userId)],
        )
