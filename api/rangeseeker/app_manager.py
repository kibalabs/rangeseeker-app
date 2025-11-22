import base64

from core.exceptions import ForbiddenException
from core.exceptions import NotFoundException
from core.exceptions import UnauthorizedException
from core.store.database import Database
from core.util import chain_util
from eth_account.messages import encode_defunct
from siwe import SiweMessage  # type: ignore[import-untyped]
from web3 import Web3

from rangeseeker.api.authorizer import Authorizer
from rangeseeker.api.v1_resources import AuthToken
from rangeseeker.api.v1_resources import PoolData
from rangeseeker.api.v1_resources import PoolHistoricalData
from rangeseeker.api.v1_resources import PricePoint
from rangeseeker.model import Agent
from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.model import Wallet
from rangeseeker.strategy_manager import StrategyManager
from rangeseeker.strategy_parser import StrategyDefinition
from rangeseeker.user_manager import UserManager

w3 = Web3()


class AppManager(Authorizer):
    def __init__(
        self,
        database: Database,
        userManager: UserManager,
        strategyManager: StrategyManager,
    ) -> None:
        self.database = database
        self.userManager = userManager
        self.strategyManager = strategyManager
        self._signatureSignerMap: dict[str, str] = {}

    async def _retrieve_signature_signer_address(self, signatureString: str) -> str:
        if signatureString in self._signatureSignerMap:
            return self._signatureSignerMap[signatureString]
        authTokenJson = base64.b64decode(signatureString).decode('utf-8')
        authToken = AuthToken.model_validate_json(authTokenJson)
        messageHash = encode_defunct(text=authToken.message)
        siweMessage = SiweMessage.from_message(message=authToken.message)
        signerId = chain_util.normalize_address(siweMessage.address)
        messageSignerId = chain_util.normalize_address(w3.eth.account.recover_message(messageHash, signature=authToken.signature))
        if messageSignerId != signerId:
            raise UnauthorizedException
        self._signatureSignerMap[signatureString] = signerId
        return signerId

    async def retrieve_signature_signer(self, signatureString: str) -> str:
        signerAddress = await self._retrieve_signature_signer_address(signatureString=signatureString)
        user = await self._get_user_by_wallet_address(walletAddress=signerAddress)
        return user.userId

    async def _get_user_by_wallet_address(self, walletAddress: str) -> User:
        try:
            user = await self.userManager.get_user_by_wallet_address(walletAddress=walletAddress)
        except NotFoundException:
            raise UnauthorizedException('NO_USER')
        return user

    async def user_login_with_wallet_address(self, walletAddress: str, userId: str) -> User:
        try:
            user = await self.userManager.get_user_by_wallet_address(walletAddress=walletAddress)
        except NotFoundException:
            raise UnauthorizedException('NO_USER')
        if user.userId != userId:
            raise ForbiddenException('INCORRECT_USER')
        return user

    async def get_user(self, userId: str) -> User:
        return await self.userManager.get_user(userId=userId)

    async def get_user_by_username(self, username: str) -> User:
        return await self.userManager.get_user_by_username(username=username)

    async def create_user(self, walletAddress: str, username: str) -> User:
        return await self.userManager.create_user(walletAddress=walletAddress, username=username)

    async def get_user_wallet(self, userId: str) -> UserWallet:
        return await self.userManager.get_user_wallet(userId=userId)

    async def list_agents(self, userId: str) -> list[Agent]:
        return await self.userManager.list_agents_by_user_id(userId=userId)

    async def get_agent(self, userId: str, agentId: str) -> Agent:
        return await self.userManager.get_agent(userId=userId, agentId=agentId)

    async def create_agent(self, userId: str, name: str, emoji: str, strategyName: str, strategyDescription: str, strategyDefinition: StrategyDefinition) -> Agent:
        strategy = await self.strategyManager.create_strategy(userId=userId, name=strategyName, description=strategyDescription, strategyDefinition=strategyDefinition)
        return await self.userManager.create_agent(userId=userId, name=name, emoji=emoji, strategyId=strategy.strategyId)

    async def get_agent_wallet(self, userId: str, agentId: str) -> Wallet:
        agentWallet = await self.userManager.get_agent_wallet(userId=userId, agentId=agentId)
        # TODO(krishan711): add asset balances
        return Wallet(
            walletAddress=agentWallet.walletAddress,
            assetBalances=[],
            delegatedSmartWallet=agentWallet.delegatedSmartWallet,
        )

    async def parse_strategy(self, description: str) -> StrategyDefinition:
        return await self.strategyManager.parse_strategy(description=description)

    async def get_pool_data(self, chainId: int, token0Address: str, token1Address: str) -> PoolData:
        token0Address = chain_util.normalize_address(token0Address)
        token1Address = chain_util.normalize_address(token1Address)
        pool = await self.strategyManager.uniswapClient.get_pool(token0Address=token0Address, token1Address=token1Address)
        poolAddress = pool.address
        currentPrice = await self.strategyManager.uniswapClient.get_current_price(poolAddress=poolAddress)
        volatilityData24h = await self.strategyManager.uniswapClient.get_pool_volatility(poolAddress=poolAddress, hoursBack=24)
        volatilityData7d = await self.strategyManager.uniswapClient.get_pool_volatility(poolAddress=poolAddress, hoursBack=168)
        feeGrowth7d = await self.strategyManager.uniswapClient.get_pool_fee_growth(poolAddress=poolAddress, hoursBack=168)
        feeRate = pool.fee / 1_000_000.0
        return PoolData(
            chainId=chainId,
            token0Address=token0Address,
            token1Address=token1Address,
            poolAddress=poolAddress,
            currentPrice=currentPrice,
            volatility24h=volatilityData24h.realized,
            volatility7d=volatilityData7d.realized,
            volatilityAnnualized=volatilityData24h.annualized,
            volatilityRealized=volatilityData24h.realized,
            feeGrowth7d=feeGrowth7d,
            feeRate=feeRate,
        )

    async def get_pool_historical_data(self, chainId: int, token0Address: str, token1Address: str, hoursBack: int) -> PoolHistoricalData:
        token0Address = chain_util.normalize_address(token0Address)
        token1Address = chain_util.normalize_address(token1Address)
        pool = await self.strategyManager.uniswapClient.get_pool(token0Address=token0Address, token1Address=token1Address)
        poolAddress = pool.address
        swaps = await self.strategyManager.uniswapClient.get_pool_swaps(poolAddress=poolAddress, hoursBack=hoursBack)
        pricePoints = []
        for swap in swaps:
            price = self.strategyManager.uniswapClient.calculate_price_from_sqrt_price_x96(swap.sqrtPriceX96)
            pricePoints.append(
                PricePoint(
                    timestamp=swap.timestamp,
                    price=price,
                )
            )
        return PoolHistoricalData(
            chainId=chainId,
            token0Address=token0Address,
            token1Address=token1Address,
            poolAddress=poolAddress,
            pricePoints=pricePoints,
        )
