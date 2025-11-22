from core.exceptions import BadRequestException
from core.exceptions import NotFoundException
from core.store.database import Database
from core.store.retriever import StringFieldFilter

from rangeseeker.external.coinbase_cdp_client import CoinbaseCdpClient
from rangeseeker.model import Agent
from rangeseeker.model import AgentWallet
from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.store import schema
from rangeseeker.store.entity_repository import UUIDFieldFilter


class UserManager:
    def __init__(
        self,
        database: Database,
        coinbaseCdpClient: CoinbaseCdpClient,
    ) -> None:
        self.database = database
        self.coinbaseCdpClient = coinbaseCdpClient

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

    async def get_agent_raw(self, agentId: str) -> Agent:
        agent = await schema.AgentsRepository.get_one(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.AgentsTable.c.agentId.key, eq=agentId)],
        )
        return agent

    async def get_agent(self, userId: str, agentId: str) -> Agent:
        agent = await self.get_agent_raw(agentId=agentId)
        if agent.userId != userId:
            raise NotFoundException('NO_AGENT')
        return agent

    async def get_agent_wallet(self, userId: str, agentId: str) -> AgentWallet:
        agent = await self.get_agent(userId=userId, agentId=agentId)
        agentWallets = await self.list_agent_wallets_by_agent_id(agentId=agent.agentId)
        if len(agentWallets) == 0:
            raise NotFoundException('NO_AGENT_WALLET')
        return agentWallets[0]

    async def list_agents_by_user_id(self, userId: str) -> list[Agent]:
        return await schema.AgentsRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.AgentsTable.c.userId.key, eq=userId)],
        )

    async def create_agent(self, userId: str, name: str, emoji: str, strategyId: str) -> Agent:
        agent = await schema.AgentsRepository.create(
            database=self.database,
            userId=userId,
            name=name,
            emoji=emoji,
            strategyId=strategyId,
        )
        walletAddress = await self.coinbaseCdpClient.create_eoa(name=agent.agentId)
        await schema.AgentWalletsRepository.create(
            database=self.database,
            agentId=agent.agentId,
            walletAddress=walletAddress,
            delegatedSmartWallet=None,
        )
        return agent

    async def list_agent_wallets_by_agent_id(self, agentId: str) -> list[AgentWallet]:
        return await schema.AgentWalletsRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.AgentWalletsTable.c.agentId.key, eq=agentId)],
        )

    async def get_agent_wallet_by_wallet_address(self, walletAddress: str) -> AgentWallet:
        return await schema.AgentWalletsRepository.get_one(
            database=self.database,
            fieldFilters=[StringFieldFilter(fieldName=schema.AgentWalletsTable.c.walletAddress.key, eq=walletAddress)],
        )

    async def get_agent_wallet_by_agent_id(self, agentId: str) -> AgentWallet:
        agentWallet = await schema.AgentWalletsRepository.get_first(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.AgentWalletsTable.c.agentId.key, eq=agentId)],
        )
        if agentWallet is None:
            raise NotFoundException('NO_AGENT_WALLET')
        return agentWallet

    async def list_all_agents(self) -> list[Agent]:
        return await schema.AgentsRepository.list_many(
            database=self.database,
            fieldFilters=[],
        )
