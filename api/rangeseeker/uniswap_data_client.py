import datetime
import math
import statistics
import typing
from typing import cast

from core.exceptions import NotFoundException
from core.util import chain_util
from pydantic import BaseModel

from rangeseeker.amp_client import AmpClient
from rangeseeker.amp_client import SqlValue

MIN_DATA_POINTS = 2


class SwapEvent(BaseModel):
    timestamp: int
    sqrtPriceX96: int
    amount0: int
    amount1: int
    liquidity: int
    tick: int
    txHash: str
    blockNumber: int


class PoolState(BaseModel):
    blockNumber: int
    timestamp: int
    sqrtPriceX96: int
    tick: int
    liquidity: int


class VolatilityData(BaseModel):
    annualized: float
    realized: float


class Pool(BaseModel):
    address: str
    token0: str
    token1: str
    fee: int
    tickSpacing: int
    liquidity: int
    sqrtPriceX96: int
    tick: int


class UniswapDataClient:
    def __init__(self, ampClient: AmpClient) -> None:
        self.ampClient = ampClient
        self.ampDatasetName = 'edgeandnode/uniswap_v3_base@0.0.1'
        self._poolAddressCache: dict[str, Pool] = {}

    async def get_pool_swaps(self, poolAddress: str, hoursBack: int = 24) -> list[SwapEvent]:
        cutoffTime = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(hours=hoursBack)
        timestampCutoff = cutoffTime.strftime('%Y-%m-%d %H:%M:%S')
        # Group by 15-minute intervals to reduce data size while maintaining good granularity
        sql = f"""
        WITH binned_swaps AS (
            SELECT
                FLOOR(EXTRACT(EPOCH FROM timestamp) / (15*60)) as time_bucket,
                timestamp,
                event."sqrtPriceX96" as sqrtPriceX96,
                block_num,
                tx_hash,
                log_index,
                event
            FROM "{self.ampDatasetName}".event__swap
            WHERE
                pool_address = {poolAddress}
                AND timestamp > TIMESTAMP '{timestampCutoff}'
        ),
        ranked_swaps AS (
            SELECT
                *,
                ROW_NUMBER() OVER (PARTITION BY time_bucket ORDER BY block_num DESC) as rn
            FROM binned_swaps
        )
        SELECT
            timestamp,
            block_num,
            tx_hash,
            log_index,
            event
        FROM ranked_swaps
        WHERE rn = 1
        ORDER BY timestamp DESC
        """
        swaps = []
        async for row in self.ampClient.execute_sql(sql):
            event = cast(dict[str, SqlValue], row.get('event', {}))
            timestamp_val = row.get('timestamp')
            timestamp = int(timestamp_val.timestamp()) if isinstance(timestamp_val, datetime.datetime) else 0
            swaps.append(
                SwapEvent(
                    timestamp=timestamp,
                    sqrtPriceX96=int(cast(int, event.get('sqrtPriceX96', 0))),
                    amount0=int(cast(int, event.get('amount0', 0))),
                    amount1=int(cast(int, event.get('amount1', 0))),
                    liquidity=int(cast(int, event.get('liquidity', 0))),
                    tick=int(cast(int, event.get('tick', 0))),
                    txHash=str(row.get('tx_hash', '')),
                    blockNumber=int(cast(int, row.get('block_num', 0))),
                )
            )
        return swaps

    async def get_pool_current_state(self, poolAddress: str) -> PoolState | None:
        sql = f"""
        SELECT
            block_num,
            timestamp,
            event
        FROM "{self.ampDatasetName}".event__swap
        WHERE
            pool_address = {poolAddress}
        ORDER BY block_num DESC
        LIMIT 1
        """
        results = [row async for row in self.ampClient.execute_sql(sql)]
        if not results:
            return None
        row = results[0]
        event = cast(dict[str, SqlValue], row.get('event', {}))
        timestamp_val = row.get('timestamp')
        timestamp = int(timestamp_val.timestamp()) if isinstance(timestamp_val, datetime.datetime) else 0
        return PoolState(
            blockNumber=int(cast(int, row.get('block_num', 0))),
            timestamp=timestamp,
            sqrtPriceX96=int(cast(int, event.get('sqrtPriceX96', 0))),
            tick=int(cast(int, event.get('tick', 0))),
            liquidity=int(cast(int, event.get('liquidity', 0))),
        )

    async def get_pool_volatility(self, poolAddress: str, hoursBack: int = 24) -> VolatilityData:
        cutoffTime = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(hours=hoursBack)
        timestampCutoff = cutoffTime.strftime('%Y-%m-%d %H:%M:%S')
        secondsInYear = 365 * 24 * 3600
        secondsInPeriod = hoursBack * 3600

        # Ensure poolAddress is treated as binary literal if it's a hex string
        poolAddressLiteral = f"X'{poolAddress[2:]}'" if poolAddress.startswith('0x') else f"'{poolAddress}'"

        sql = f"""
        WITH prices AS (
            SELECT
                timestamp,
                POWER(CAST(event."sqrtPriceX96" AS DOUBLE) / 79228162514264337593543950336.0, 2) as price
            FROM "{self.ampDatasetName}".event__swap
            WHERE
                pool_address = {poolAddressLiteral}
                AND timestamp > TIMESTAMP '{timestampCutoff}'
        ),
        returns AS (
            SELECT
                timestamp,
                LN(price / LAG(price) OVER (ORDER BY timestamp)) as log_return
            FROM prices
            WHERE price > 0
        ),
        stats AS (
            SELECT
                STDDEV(log_return) as std_dev,
                COUNT(*) as count,
                EXTRACT(EPOCH FROM MAX(timestamp)) - EXTRACT(EPOCH FROM MIN(timestamp)) as duration_seconds
            FROM returns
            WHERE log_return IS NOT NULL
        )
        SELECT
            CASE
                WHEN duration_seconds > 0 AND count >= {MIN_DATA_POINTS} THEN std_dev * SQRT((count / duration_seconds) * {secondsInYear})
                ELSE 0
            END as annualized_volatility,
            CASE
                WHEN duration_seconds > 0 AND count >= {MIN_DATA_POINTS} THEN std_dev * SQRT((count / duration_seconds) * {secondsInPeriod})
                ELSE 0
            END as realized_volatility
        FROM stats
        """
        results = [row async for row in self.ampClient.execute_sql(sql)]
        if not results:
            return VolatilityData(annualized=0.0, realized=0.0)

        row = results[0]
        return VolatilityData(annualized=float(cast(float, row.get('annualized_volatility', 0.0))), realized=float(cast(float, row.get('realized_volatility', 0.0))))

    async def get_current_price(self, poolAddress: str, token0Decimals: int = 18, token1Decimals: int = 6) -> float:
        state = await self.get_pool_current_state(poolAddress)
        if not state:
            return 0.0
        return self.calculate_price_from_sqrt_price_x96(state.sqrtPriceX96, token0Decimals, token1Decimals)

    def calculate_price_from_sqrt_price_x96(self, sqrtPriceX96: int, token0Decimals: int = 18, token1Decimals: int = 6) -> float:
        sqrtPrice = sqrtPriceX96 / (2**96)
        price = sqrtPrice**2
        adjustedPrice: float = price * (10**token0Decimals) / (10**token1Decimals)
        return adjustedPrice

    async def get_pool(self, token0Address: str, token1Address: str, feeTier: int | None = None) -> Pool:
        t0 = chain_util.normalize_address(token0Address)
        t1 = chain_util.normalize_address(token1Address)
        cacheKey = f'{t0}-{t1}-{feeTier}'
        if cacheKey in self._poolAddressCache:
            return self._poolAddressCache[cacheKey]
        # Step 1: Get all pools for the pair
        sql_pools = f"""
        SELECT
            event."pool" as pool_address,
            event."token0" as token0,
            event."token1" as token1,
            event."fee" as fee,
            event."tickSpacing" as tick_spacing
        FROM "{self.ampDatasetName}".event__factory_pool_created
        WHERE
            (event."token0" = {t0} AND event."token1" = {t1})
            OR
            (event."token0" = {t1} AND event."token1" = {t0})
        """
        pool_results = [row async for row in self.ampClient.execute_sql(sql_pools)]
        if not pool_results:
            raise NotFoundException
        pools_map = {}
        pool_addresses = []
        for row in pool_results:
            poolAddressRaw = row.get('pool_address')
            poolAddress = '0x' + poolAddressRaw.hex() if isinstance(poolAddressRaw, bytes) else str(poolAddressRaw)
            poolAddress = chain_util.normalize_address(poolAddress)
            pools_map[poolAddress] = row
            pool_addresses.append(poolAddress)
        if not pool_addresses:
            raise NotFoundException
        # Step 2: Get latest state for all pools
        # Use UNION ALL to get latest state for each pool individually, avoiding massive window functions
        subqueries = [
            f"""
                (SELECT
                    pool_address,
                    event
                FROM "{self.ampDatasetName}".event__swap
                WHERE pool_address = X'{addr[2:]}'
                ORDER BY block_num DESC
                LIMIT 1)
            """
            for addr in pool_addresses
        ]
        sql_state = ' UNION ALL '.join(subqueries)
        state_results = [row async for row in self.ampClient.execute_sql(sql_state)]
        states_map: dict[str, typing.Any] = {}  # type: ignore[explicit-any]
        for row in state_results:
            poolAddressRaw = row.get('pool_address')
            poolAddress = '0x' + poolAddressRaw.hex() if isinstance(poolAddressRaw, bytes) else str(poolAddressRaw)
            poolAddress = chain_util.normalize_address(poolAddress)
            states_map[poolAddress] = row.get('event')
        pools: list[Pool] = []
        for poolAddress, row in pools_map.items():
            swapEvent = states_map.get(poolAddress)
            liquidity = 0
            sqrtPriceX96 = 0
            tick = 0
            if swapEvent and isinstance(swapEvent, dict):
                liquidity = int(cast(int, swapEvent.get('liquidity', 0)))
                sqrtPriceX96 = int(cast(int, swapEvent.get('sqrtPriceX96', 0)))
                tick = int(cast(int, swapEvent.get('tick', 0)))
            token0Raw = row.get('token0')
            token0 = '0x' + token0Raw.hex() if isinstance(token0Raw, bytes) else str(token0Raw)
            token1Raw = row.get('token1')
            token1 = '0x' + token1Raw.hex() if isinstance(token1Raw, bytes) else str(token1Raw)
            pools.append(
                Pool(
                    address=poolAddress,
                    token0=chain_util.normalize_address(token0),
                    token1=chain_util.normalize_address(token1),
                    fee=int(cast(int, row.get('fee', 0))),
                    tickSpacing=int(cast(int, row.get('tick_spacing', 0))),
                    liquidity=liquidity,
                    sqrtPriceX96=sqrtPriceX96,
                    tick=tick,
                )
            )
        if not pools:
            raise NotFoundException
        selectedPool = min(pools, key=lambda p: abs(p.fee - feeTier)) if feeTier is not None else max(pools, key=lambda p: p.liquidity)
        self._poolAddressCache[cacheKey] = selectedPool
        return selectedPool

    def calculate_volatility(self, swaps: list[SwapEvent]) -> float:
        if len(swaps) < MIN_DATA_POINTS:
            return 0.0
        prices = []
        for swap in swaps:
            price = self.calculate_price_from_sqrt_price_x96(swap.sqrtPriceX96)
            if price > 0:
                prices.append(price)
        if len(prices) < MIN_DATA_POINTS:
            return 0.0
        prices.reverse()
        logReturns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices)) if prices[i - 1] > 0]
        if not logReturns:
            return 0.0
        stdDev = statistics.stdev(logReturns) if len(logReturns) > 1 else 0.0
        timeSpanHours = (swaps[0].timestamp - swaps[-1].timestamp) / 3600
        if timeSpanHours <= 0:
            return 0.0
        swapsPerHour = len(swaps) / timeSpanHours
        annualizationFactor = math.sqrt(swapsPerHour * 24 * 365)
        annualizedVol = stdDev * annualizationFactor
        return annualizedVol
