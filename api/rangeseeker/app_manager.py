import asyncio
import base64
import datetime
import math
import typing
from typing import cast

from core import logging
from core.caching.dict_cache import DictCache
from core.exceptions import ForbiddenException
from core.exceptions import KibaException
from core.exceptions import NotFoundException
from core.exceptions import UnauthorizedException
from core.store.database import Database
from core.util import chain_util
from core.util.typing_util import JsonObject
from core.web3.eth_client import RestEthClient
from eth_account.messages import encode_defunct
from siwe import SiweMessage  # type: ignore[import-untyped]
from web3.types import HexStr
from web3.types import TxParams
from web3.types import Wei

from rangeseeker import constants
from rangeseeker.api.authorizer import Authorizer
from rangeseeker.api.v1_resources import AuthToken
from rangeseeker.api.v1_resources import PoolData
from rangeseeker.api.v1_resources import PoolHistoricalData
from rangeseeker.api.v1_resources import PricePoint
from rangeseeker.erc_abis import ERC20_ABI
from rangeseeker.external.pyth_client import PythClient
from rangeseeker.external.zerox_client import ZeroxClient
from rangeseeker.model import Agent
from rangeseeker.model import Asset
from rangeseeker.model import AssetBalance
from rangeseeker.model import AssetPrice
from rangeseeker.model import PreviewDeposit
from rangeseeker.model import Strategy
from rangeseeker.model import UniswapPosition
from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.model import Wallet
from rangeseeker.strategy_manager import StrategyManager
from rangeseeker.strategy_parser import StrategyDefinition
from rangeseeker.user_manager import UserManager

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
        ethClient: RestEthClient,
        zeroxClient: ZeroxClient,
    ) -> None:
        self.database = database
        self.userManager = userManager
        self.strategyManager = strategyManager
        self.pythClient = pythClient
        self.ethClient = ethClient
        self.zeroxClient = zeroxClient
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
        messageSignerId = chain_util.normalize_address(self.ethClient.w3.eth.account.recover_message(messageHash, signature=authToken.signature))
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
        assetBalances, uniswapPositions = await asyncio.gather(
            self.get_wallet_balances(chainId=8453, walletAddress=agentWallet.walletAddress),
            self.get_wallet_uniswap_positions(walletAddress=agentWallet.walletAddress),
        )
        return Wallet(
            walletAddress=agentWallet.walletAddress,
            assetBalances=assetBalances,
            uniswapPositions=uniswapPositions,
            delegatedSmartWallet=agentWallet.delegatedSmartWallet,
        )

    async def get_wallet_balances(self, chainId: int, walletAddress: str) -> list[AssetBalance]:
        clientBalances = await self.userManager.coinbaseCdpClient.get_wallet_asset_balances(chainId=chainId, walletAddress=walletAddress)
        prices = await self.pythClient.get_prices(priceIds=[PYTH_ETH_USD_PRICE_ID, PYTH_USDC_USD_PRICE_ID])
        assetBalances = []
        for clientBalance in clientBalances:
            # Skip Uniswap V3 NFT positions - we'll show those separately
            if clientBalance.symbol == 'UNI-V3-POS':
                continue
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

    async def get_wallet_uniswap_positions(self, walletAddress: str) -> list[UniswapPosition]:
        positions = await self.strategyManager.uniswapClient.get_wallet_positions(walletAddress=walletAddress)
        prices = await self.pythClient.get_prices(priceIds=[PYTH_ETH_USD_PRICE_ID, PYTH_USDC_USD_PRICE_ID])
        ethPriceUsd = prices.get(PYTH_ETH_USD_PRICE_ID, 0.0)
        usdcPriceUsd = prices.get(PYTH_USDC_USD_PRICE_ID, 0.0)

        uniswapPositions = []
        for position in positions:
            # For now, hardcode WETH/USDC since that's what we're using
            # TODO: Fetch token details from on-chain or TheGraph
            token0 = Asset(
                assetId=constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID],
                createdDate=datetime.datetime.now(tz=datetime.UTC),
                updatedDate=datetime.datetime.now(tz=datetime.UTC),
                chainId=constants.BASE_CHAIN_ID,
                address=constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID],
                name='Wrapped Ether',
                symbol='WETH',
                decimals=18,
            )
            token1 = Asset(
                assetId=constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID],
                createdDate=datetime.datetime.now(tz=datetime.UTC),
                updatedDate=datetime.datetime.now(tz=datetime.UTC),
                chainId=constants.BASE_CHAIN_ID,
                address=constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID],
                name='USD Coin',
                symbol='USDC',
                decimals=6,
            )

            # Calculate USD values
            token0ValueUsd = (position.amount0 / 10**18) * ethPriceUsd
            token1ValueUsd = (position.amount1 / 10**6) * usdcPriceUsd
            totalValueUsd = token0ValueUsd + token1ValueUsd

            uniswapPositions.append(
                UniswapPosition(
                    tokenId=position.tokenId,
                    poolAddress=position.poolAddress or '',
                    token0=token0,
                    token1=token1,
                    token0Amount=position.amount0,
                    token1Amount=position.amount1,
                    token0ValueUsd=token0ValueUsd,
                    token1ValueUsd=token1ValueUsd,
                    totalValueUsd=totalValueUsd,
                )
            )

        return uniswapPositions

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

    async def _get_erc20_allowance(self, chainId: int, assetAddress: str, walletAddress: str, spenderAddress: str) -> int:  # noqa: ARG002
        currentAllowanceResponse = await self.ethClient.call_function_by_name(
            toAddress=assetAddress,
            contractAbi=ERC20_ABI,
            functionName='allowance',
            fromAddress=walletAddress,
            arguments={
                'owner': walletAddress,
                'spender': spenderAddress,
            },
        )
        return int(currentAllowanceResponse[0])

    async def _approve_token_if_needed(self, chainId: int, walletAddress: str, assetAddress: str, spenderAddress: str, amount: int) -> None:
        currentAllowance = await self._get_erc20_allowance(
            chainId=chainId,
            assetAddress=assetAddress,
            walletAddress=walletAddress,
            spenderAddress=spenderAddress,
        )
        logging.info(f'[APPROVE] Current allowance for {assetAddress} -> {spenderAddress}: {currentAllowance}')
        if currentAllowance < amount:
            logging.info(f'[APPROVE] Insufficient allowance ({currentAllowance} < {amount}). Approving for max amount')
            maxUint256 = 2**256 - 1
            transactionDict: TxParams = {
                'from': chain_util.normalize_address(value=walletAddress),
                'to': chain_util.normalize_address(value=assetAddress),
                'value': Wei(0),
                'data': chain_util.encode_transaction_data_by_name(
                    contractAbi=ERC20_ABI,
                    functionName='approve',
                    arguments={
                        'spender': spenderAddress,
                        'amount': maxUint256,
                    },
                ),
            }
            filledTransaction = await self.ethClient.fill_transaction_params(
                params=transactionDict,
                fromAddress=walletAddress,
                chainId=chainId,
            )
            signedTx = await self.userManager.coinbaseCdpClient.sign_transaction(
                walletAddress=walletAddress,
                transactionDict=filledTransaction,
            )
            txHash = await self.ethClient.send_raw_transaction(transactionData=signedTx)
            logging.info(f'[APPROVE] Approval transaction broadcast: {txHash}')
            receipt = await self.ethClient.wait_for_transaction_receipt(transactionHash=txHash)
            logging.info(f'[APPROVE] Approval mined in block {receipt["blockNumber"]}')
            await asyncio.sleep(3)
            newAllowance = await self._get_erc20_allowance(
                chainId=chainId,
                assetAddress=assetAddress,
                walletAddress=walletAddress,
                spenderAddress=spenderAddress,
            )
            logging.info(f'[APPROVE] New allowance after approval: {newAllowance}')
        else:
            logging.info(f'[APPROVE] Allowance already sufficient ({currentAllowance} >= {amount})')

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

    async def deposit_made_to_agent(self, userId: str, agentId: str) -> None:
        logging.info(f'[REBALANCE] Starting rebalance for agent {agentId}')
        agent = await self.userManager.get_agent(userId=userId, agentId=agentId)
        agentWallet = await self.userManager.get_agent_wallet(userId=userId, agentId=agent.agentId)
        logging.info(f'[REBALANCE] Agent wallet address: {agentWallet.walletAddress}')
        strategy = await self.strategyManager.get_strategy(strategyId=agent.strategyId)
        logging.info(f'[REBALANCE] Strategy loaded: {strategy.strategyId}')
        balances = await self.get_wallet_balances(chainId=8453, walletAddress=agentWallet.walletAddress)
        logging.info(f'[REBALANCE] Fetched {len(balances)} token balances')
        wethBalance = next((b for b in balances if b.asset.address == constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID]), None)
        usdcBalance = next((b for b in balances if b.asset.address == constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID]), None)
        if not wethBalance or not usdcBalance:
            logging.error(f'[REBALANCE] Missing balances - WETH: {wethBalance is not None}, USDC: {usdcBalance is not None}')
            raise KibaException('Agent wallet must have WETH and USDC balances')
        token0Amount = float(wethBalance.balance) / (10**wethBalance.asset.decimals)
        token1Amount = float(usdcBalance.balance) / (10**usdcBalance.asset.decimals)
        logging.info(f'[REBALANCE] Current balances - WETH: {token0Amount:.6f}, USDC: {token1Amount:.2f}')
        # 2. Calculate optimal swap amounts using existing logic
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
        optimalRatio = amount1Unit / amount0Unit
        totalValueUsd = (token1Amount * usdcPrice) + (token0Amount * ethPrice)
        xFinal = totalValueUsd / (ethPrice + (optimalRatio * usdcPrice))
        yFinal = xFinal * optimalRatio
        wethDiff = xFinal - token0Amount
        usdcDiff = yFinal - token1Amount
        logging.info(f'[REBALANCE] Optimal amounts - WETH: {xFinal:.6f}, USDC: {yFinal:.2f}')
        logging.info(f'[REBALANCE] Differences - WETH: {wethDiff:.6f}, USDC: {usdcDiff:.2f}')
        if wethDiff > MIN_WETH_DIFF:
            swapAmountUsdc = int(-usdcDiff * (10**usdcBalance.asset.decimals))
            logging.info(f'[REBALANCE] Swapping {-usdcDiff:.2f} USDC for {wethDiff:.6f} WETH (amount: {swapAmountUsdc})')
            await self._execute_swap(
                chainId=8453,
                walletAddress=agentWallet.walletAddress,
                fromToken=constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID],
                toToken=constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID],
                fromAmount=str(swapAmountUsdc),
            )
            logging.info('[REBALANCE] Swap completed successfully')
        elif usdcDiff > MIN_USDC_DIFF:
            swapAmountWeth = int(-wethDiff * (10**wethBalance.asset.decimals))
            logging.info(f'[REBALANCE] Swapping {-wethDiff:.6f} WETH for {usdcDiff:.2f} USDC (amount: {swapAmountWeth})')
            await self._execute_swap(
                chainId=8453,
                walletAddress=agentWallet.walletAddress,
                fromToken=constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID],
                toToken=constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID],
                fromAmount=str(swapAmountWeth),
            )
            logging.info('[REBALANCE] Swap completed successfully')
        else:
            logging.info('[REBALANCE] No swap needed - balances already optimal')
        logging.info('[REBALANCE] Fetching updated balances after swap')
        balances = await self.get_wallet_balances(chainId=8453, walletAddress=agentWallet.walletAddress)
        wethBalance = next((b for b in balances if b.asset.address == constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID]), None)
        usdcBalance = next((b for b in balances if b.asset.address == constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID]), None)
        if not wethBalance or not usdcBalance:
            logging.error('[REBALANCE] Failed to get updated balances after swap')
            raise KibaException('Failed to get updated balances after swap')
        finalWethAmount = float(wethBalance.balance) / (10**wethBalance.asset.decimals)
        finalUsdcAmount = float(usdcBalance.balance) / (10**usdcBalance.asset.decimals)
        logging.info(f'[REBALANCE] Final balances - WETH: {finalWethAmount:.6f}, USDC: {finalUsdcAmount:.2f}')
        logging.info(f'[REBALANCE] Starting Uniswap V3 deposit - WETH: {wethBalance.balance}, USDC: {usdcBalance.balance}')
        await self._deposit_to_uniswap_v3(
            chainId=8453,
            walletAddress=agentWallet.walletAddress,
            wethAmount=wethBalance.balance,
            usdcAmount=usdcBalance.balance,
            priceLower=priceLower,
            priceUpper=priceUpper,
        )
        logging.info('[REBALANCE] Rebalance completed successfully!')

    async def _execute_swap(self, chainId: int, walletAddress: str, fromToken: str, toToken: str, fromAmount: str) -> None:
        logging.info(f'[SWAP] Executing swap - from: {fromToken}, to: {toToken}, amount: {fromAmount}')
        amount = int(fromAmount)
        swapResponse = await self.zeroxClient.prepare_quote(
            chainId=chainId,
            amount=amount,
            fromAssetAddress=fromToken,
            toAssetAddress=toToken,
            fromWalletAddress=walletAddress,
        )
        logging.info('[SWAP] 0x swap response received')
        allowanceIssue = swapResponse['issues'].get('allowance')
        if allowanceIssue:
            spender = typing.cast(str | None, allowanceIssue.get('spender'))
            if spender:
                spender = chain_util.normalize_address(value=spender)
                logging.info(f'[SWAP] Allowance issue detected for spender: {spender}')
                await self._approve_token_if_needed(
                    chainId=chainId,
                    walletAddress=walletAddress,
                    assetAddress=fromToken,
                    spenderAddress=spender,
                    amount=amount,
                )
                logging.info('[SWAP] Refreshing swap quote after approval')
                swapResponse = await self.zeroxClient.prepare_quote(
                    chainId=chainId,
                    amount=amount,
                    fromAssetAddress=fromToken,
                    toAssetAddress=toToken,
                    fromWalletAddress=walletAddress,
                )
                logging.info('[SWAP] Refreshed swap response received')
        transactionData = swapResponse['transaction']
        toAddress = chain_util.normalize_address(value=typing.cast(str, transactionData['to']))
        data = typing.cast(str, transactionData['data'])
        value = int(typing.cast(str, transactionData.get('value', '0')))
        gasFromSwap = int(typing.cast(str, transactionData.get('gas', '300000')))
        logging.info(f'[SWAP] Transaction details - to: {toAddress}, value: {value}, gas: {gasFromSwap}, data length: {len(data)}')

        # Build base transaction params
        transactionDict: TxParams = {
            'from': chain_util.normalize_address(value=walletAddress),
            'to': chain_util.normalize_address(value=toAddress),
            'value': Wei(value),
            'data': typing.cast(HexStr, data),
        }

        # Fill in gas, nonce, and fee parameters automatically
        filledTransaction = await self.ethClient.fill_transaction_params(
            params=transactionDict,
            fromAddress=walletAddress,
            gas=gasFromSwap,
            chainId=chainId,
        )

        signedTx = await self.userManager.coinbaseCdpClient.sign_transaction(
            walletAddress=walletAddress,
            transactionDict=filledTransaction,
        )
        logging.info('[SWAP] Transaction signed, broadcasting...')
        try:
            txHash = await self.ethClient.send_raw_transaction(transactionData=signedTx)
            logging.info(f'[SWAP] Transaction broadcast successfully: {txHash}')
            receipt = await self.ethClient.wait_for_transaction_receipt(transactionHash=txHash)
            logging.info(f'[SWAP] Transaction mined in block {receipt["blockNumber"]}, status: {receipt["status"]}')
        except Exception as e:
            logging.exception(f'[SWAP] Transaction failed: {e}')
            logging.exception(f'[SWAP] Transaction dict: {transactionDict}')
            raise

    async def _deposit_to_uniswap_v3(self, chainId: int, walletAddress: str, wethAmount: int, usdcAmount: int, priceLower: float, priceUpper: float) -> None:
        logging.info(f'[UNISWAP] Calculating ticks - priceLower: {priceLower:.2f}, priceUpper: {priceUpper:.2f}')
        tickLower = math.floor(math.log(priceLower, 1.0001))
        tickUpper = math.ceil(math.log(priceUpper, 1.0001))
        tickSpacing = 10
        tickLower = int((tickLower // tickSpacing) * tickSpacing)
        tickUpper = int((tickUpper // tickSpacing) * tickSpacing)
        logging.info(f'[UNISWAP] Ticks calculated - lower: {tickLower}, upper: {tickUpper}')
        positionManagerAddress = constants.CHAIN_UNISWAP_V3_NONFUNGIBLE_POSITION_MANAGER_MAP[chainId]
        token0 = constants.CHAIN_WETH_MAP[chainId]
        token1 = constants.CHAIN_USDC_MAP[chainId]
        fee = 500  # 0.05% fee tier
        amount0Min = 0  # Allow any amount of token0 (more flexible for price movements)
        amount1Min = 0  # Allow any amount of token1 (more flexible for price movements)
        deadline = int(datetime.datetime.now(tz=datetime.UTC).timestamp()) + 1200
        logging.info(f'[UNISWAP] Token amounts - WETH: {wethAmount}, USDC: {usdcAmount}, deadline: {deadline}')
        logging.info(f'[UNISWAP] Checking/approving WETH ({token0}) to position manager')
        await self._approve_token_if_needed(chainId, walletAddress, token0, positionManagerAddress, wethAmount)
        logging.info(f'[UNISWAP] Checking/approving USDC ({token1}) to position manager')
        await self._approve_token_if_needed(chainId, walletAddress, token1, positionManagerAddress, usdcAmount)
        logging.info('[UNISWAP] Token approval checks completed')
        # Encode mint call data (simplified - using hex encoding)
        # In production, use proper ABI encoder like eth_abi
        data = self._encode_mint_params(
            token0=token0,
            token1=token1,
            fee=fee,
            tickLower=tickLower,
            tickUpper=tickUpper,
            amount0Desired=wethAmount,
            amount1Desired=usdcAmount,
            amount0Min=amount0Min,
            amount1Min=amount1Min,
            recipient=walletAddress,
            deadline=deadline,
        )
        logging.info('[UNISWAP] Broadcasting mint transaction')
        transactionDict: TxParams = {
            'from': chain_util.normalize_address(value=walletAddress),
            'to': chain_util.normalize_address(value=positionManagerAddress),
            'value': Wei(0),
            'data': typing.cast(HexStr, data),
        }
        filledTransaction = await self.ethClient.fill_transaction_params(
            params=transactionDict,
            fromAddress=walletAddress,
            chainId=chainId,
        )
        signedTx = await self.userManager.coinbaseCdpClient.sign_transaction(
            walletAddress=walletAddress,
            transactionDict=filledTransaction,
        )
        txHash = await self.ethClient.send_raw_transaction(transactionData=signedTx)
        logging.info(f'[UNISWAP] Mint transaction broadcast successfully: {txHash}')
        receipt = await self.ethClient.wait_for_transaction_receipt(transactionHash=txHash)
        logging.info(f'[UNISWAP] Mint transaction mined in block {receipt["blockNumber"]}')

    def _encode_mint_params(self, token0: str, token1: str, fee: int, tickLower: int, tickUpper: int, amount0Desired: int, amount1Desired: int, amount0Min: int, amount1Min: int, recipient: str, deadline: int) -> str:
        functionSelector = '0x88316456'
        params = [
            token0[2:].zfill(64),
            token1[2:].zfill(64),
            f'{fee:x}'.zfill(64),
            f'{tickLower & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:x}'.zfill(64),
            f'{tickUpper & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:x}'.zfill(64),
            f'{amount0Desired:x}'.zfill(64),
            f'{amount1Desired:x}'.zfill(64),
            f'{amount0Min:x}'.zfill(64),
            f'{amount1Min:x}'.zfill(64),
            recipient[2:].zfill(64),
            f'{deadline:x}'.zfill(64),
        ]
        return functionSelector + ''.join(params)
