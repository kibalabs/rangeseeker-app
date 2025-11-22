from core.store.database import Database

from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.user_manager import UserManager


class AppManager:
    def __init__(self, database: Database, userManager: UserManager) -> None:
        self.database = database
        self.userManager = userManager

    async def get_user(self, userId: str) -> User:
        return await self.userManager.get_user(userId=userId)

    async def get_user_by_wallet_address(self, walletAddress: str) -> User:
        return await self.userManager.get_user_by_wallet_address(walletAddress=walletAddress)

    async def get_user_by_username(self, username: str) -> User:
        return await self.userManager.get_user_by_username(username=username)

    async def create_user(self, walletAddress: str, username: str) -> User:
        return await self.userManager.create_user(walletAddress=walletAddress, username=username)

    async def get_user_wallet(self, userId: str) -> UserWallet:
        return await self.userManager.get_user_wallet(userId=userId)
