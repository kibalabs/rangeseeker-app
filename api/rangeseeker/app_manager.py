import base64
import datetime
import math
from typing import cast

from core.caching.dict_cache import DictCache
from core.exceptions import ForbiddenException
from core.exceptions import NotFoundException
from core.exceptions import UnauthorizedException
from core.store.database import Database
from core.util import chain_util
from core.util.typing_util import JsonObject
from eth_account.messages import encode_defunct
from siwe import SiweMessage  # type: ignore[import-untyped]
from web3 import Web3

from rangeseeker import constants
from rangeseeker.api.authorizer import Authorizer
from rangeseeker.api.v1_resources import AuthToken
from rangeseeker.api.v1_resources import PoolData
from rangeseeker.api.v1_resources import PoolHistoricalData
from rangeseeker.api.v1_resources import PricePoint
from rangeseeker.external.pyth_client import PythClient
from rangeseeker.model import Agent
from rangeseeker.model import Asset
from rangeseeker.model import AssetBalance
from rangeseeker.model import AssetPrice
from rangeseeker.model import PreviewDeposit
from rangeseeker.model import Strategy
from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.model import Wallet
from rangeseeker.strategy_manager import StrategyManager
from rangeseeker.strategy_parser import StrategyDefinition
from rangeseeker.user_manager import UserManager

w3 = Web3()

PYTH_ETH_USD_PRICE_ID = '0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace'
PYTH_USDC_USD_PRICE_ID = '0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a'
MIN_WETH_DIFF = 0.0001
MIN_USDC_DIFF = 0.01


class AppManager(Authorizer):
    def __init__(
        self,
        database: Database,
        userManager: UserManager,
        strategyManager: StrategyManager,
        pythClient: PythClient,
    ) -> None:
        self.database = database
        self.userManager = userManager
        self.strategyManager = strategyManager
        self.pythClient = pythClient
        self._signatureSignerMap: dict[str, str] = {}
        self._poolDataCache = DictCache()
        self._poolHistoricalDataCache = DictCache()

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

    async def get_strategy(self, userId: str, strategyId: str) -> Strategy:
        strategy = await self.strategyManager.get_strategy(strategyId=strategyId)
        if strategy.userId != userId:
            raise ForbiddenException('INCORRECT_USER')
        return strategy

    async def create_agent(self, userId: str, name: str, emoji: str, strategyName: str, strategyDescription: str, strategyDefinition: StrategyDefinition) -> Agent:
        strategy = await self.strategyManager.create_strategy(userId=userId, name=strategyName, description=strategyDescription, strategyDefinition=strategyDefinition)
        return await self.userManager.create_agent(userId=userId, name=name, emoji=emoji, strategyId=strategy.strategyId)

    async def get_agent_wallet(self, userId: str, agentId: str) -> Wallet:
        agentWallet = await self.userManager.get_agent_wallet(userId=userId, agentId=agentId)
        assetBalances = await self.get_wallet_balances(chainId=8453, walletAddress=agentWallet.walletAddress)
        return Wallet(
            walletAddress=agentWallet.walletAddress,
            assetBalances=assetBalances,
            delegatedSmartWallet=agentWallet.delegatedSmartWallet,
        )

    async def get_wallet_balances(self, chainId: int, walletAddress: str) -> list[AssetBalance]:
        clientBalances = await self.userManager.coinbaseCdpClient.get_wallet_asset_balances(chainId=chainId, walletAddress=walletAddress)
        prices = await self.pythClient.get_prices(priceIds=[PYTH_ETH_USD_PRICE_ID, PYTH_USDC_USD_PRICE_ID])
        assetBalances = []
        for clientBalance in clientBalances:
            price = 0.0
            if clientBalance.assetAddress == constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID]:
                price = prices.get(PYTH_USDC_USD_PRICE_ID, 0.0)
            elif clientBalance.assetAddress == constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID]:
                price = prices.get(PYTH_ETH_USD_PRICE_ID, 0.0)
            asset = Asset(
                assetId=clientBalance.assetAddress,
                createdDate=datetime.datetime.now(tz=datetime.UTC),
                updatedDate=datetime.datetime.now(tz=datetime.UTC),
                chainId=chainId,
                address=clientBalance.assetAddress,
                name=clientBalance.name,
                symbol=clientBalance.symbol,
                decimals=clientBalance.decimals,
            )
            assetPrice = AssetPrice(
                assetPriceId=0,
                createdDate=datetime.datetime.now(tz=datetime.UTC),
                updatedDate=datetime.datetime.now(tz=datetime.UTC),
                assetId=clientBalance.assetAddress,
                priceUsd=price,
                date=datetime.datetime.now(tz=datetime.UTC),
            )
            assetBalances.append(AssetBalance(asset=asset, assetPrice=assetPrice, balance=clientBalance.balance))
        return assetBalances

    async def parse_strategy(self, description: str) -> StrategyDefinition:
        return await self.strategyManager.parse_strategy(description=description)

    async def get_pool_data(self, chainId: int, token0Address: str, token1Address: str) -> PoolData:
        token0Address = chain_util.normalize_address(token0Address)
        token1Address = chain_util.normalize_address(token1Address)
        cacheKey = f'pool_data:{chainId}:{token0Address}:{token1Address}'
        cachedData = await self._poolDataCache.get(key=cacheKey)
        if cachedData is not None:
            return PoolData.model_validate_json(cachedData)
        pool = await self.strategyManager.uniswapClient.get_pool(token0Address=token0Address, token1Address=token1Address)
        poolAddress = pool.address
        currentPrice = await self.strategyManager.uniswapClient.get_current_price(poolAddress=poolAddress)
        volatilityData24h = await self.strategyManager.uniswapClient.get_pool_volatility(poolAddress=poolAddress, hoursBack=24)
        volatilityData7d = await self.strategyManager.uniswapClient.get_pool_volatility(poolAddress=poolAddress, hoursBack=168)
        feeGrowth7d = await self.strategyManager.uniswapClient.get_pool_fee_growth(poolAddress=poolAddress, hoursBack=168)
        feeRate = pool.fee / 1_000_000.0
        poolData = PoolData(
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
        await self._poolDataCache.set(key=cacheKey, value=poolData.model_dump_json(), expirySeconds=60 * 10)
        return poolData

    async def get_pool_historical_data(self, chainId: int, token0Address: str, token1Address: str, hoursBack: int) -> PoolHistoricalData:
        token0Address = chain_util.normalize_address(token0Address)
        token1Address = chain_util.normalize_address(token1Address)
        cacheKey = f'pool_historical_data:{chainId}:{token0Address}:{token1Address}:{hoursBack}'
        cachedData = await self._poolHistoricalDataCache.get(key=cacheKey)
        if cachedData is not None:
            return PoolHistoricalData.model_validate_json(cachedData)
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
        poolHistoricalData = PoolHistoricalData(
            chainId=chainId,
            token0Address=token0Address,
            token1Address=token1Address,
            poolAddress=poolAddress,
            pricePoints=pricePoints,
        )
        await self._poolHistoricalDataCache.set(key=cacheKey, value=poolHistoricalData.model_dump_json(), expirySeconds=60 * 10)
        return poolHistoricalData

    async def preview_deposit(self, userId: str, agentId: str, token0Amount: float, token1Amount: float) -> PreviewDeposit:
        agent = await self.get_agent(userId=userId, agentId=agentId)
        strategy = await self.get_strategy(userId=userId, strategyId=agent.strategyId)
        prices = await self.pythClient.get_prices(priceIds=[PYTH_ETH_USD_PRICE_ID, PYTH_USDC_USD_PRICE_ID])
        ethPrice = prices.get(PYTH_ETH_USD_PRICE_ID, 0.0)
        usdcPrice = prices.get(PYTH_USDC_USD_PRICE_ID, 1.0)
        if usdcPrice == 0:
            usdcPrice = 1.0
        currentPrice = ethPrice / usdcPrice
        rangePercent = 0.1
        rules = strategy.rulesJson
        for rule in rules:
            if rule.get('type') == 'RANGE_WIDTH':
                params = cast(JsonObject, rule.get('parameters', {}))
                rangePercent = float(cast(float, params.get('baseRangePercent', 10))) / 100.0
                break
        priceLower = currentPrice * (1 - rangePercent)
        priceUpper = currentPrice * (1 + rangePercent)
        sqrtP = math.sqrt(currentPrice)
        sqrtPl = math.sqrt(priceLower)
        sqrtPu = math.sqrt(priceUpper)
        amount0Unit = (1 / sqrtP) - (1 / sqrtPu)
        amount1Unit = sqrtP - sqrtPl
        optimalRatio = amount1Unit / amount0Unit  # USDC / WETH
        totalValueUsd = (token1Amount * usdcPrice) + (token0Amount * ethPrice)
        xFinal = totalValueUsd / (ethPrice + (optimalRatio * usdcPrice))
        yFinal = xFinal * optimalRatio
        wethDiff = xFinal - token0Amount
        usdcDiff = yFinal - token1Amount
        swapDescription = ''
        if wethDiff > MIN_WETH_DIFF:
            swapDescription = f'Swap {-usdcDiff:.2f} USDC for {wethDiff:.4f} WETH'
        elif usdcDiff > MIN_USDC_DIFF:
            swapDescription = f'Swap {-wethDiff:.4f} WETH for {usdcDiff:.2f} USDC'
        else:
            swapDescription = 'No swap needed'
        depositDescription = f'Deposit {xFinal:.4f} WETH and {yFinal:.2f} USDC into pool'
        return PreviewDeposit(
            swapDescription=swapDescription,
            depositDescription=depositDescription,
            token0Amount=xFinal,
            token1Amount=yFinal,
            token0Symbol='WETH',
            token1Symbol='USDC',
        )
