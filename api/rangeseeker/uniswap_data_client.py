import datetime
import math
import statistics
from dataclasses import dataclass
from typing import cast

from rangeseeker.amp_client import AmpClient
from rangeseeker.amp_client import SqlValue

MIN_DATA_POINTS = 2


@dataclass
class SwapEvent:
    timestamp: int
    sqrtPriceX96: int
    amount0: int
    amount1: int
    liquidity: int
    tick: int
    txHash: str
    blockNumber: int


@dataclass
class PoolState:
    blockNumber: int
    timestamp: int
    sqrtPriceX96: int
    tick: int
    liquidity: int


class UniswapDataClient:
    def __init__(self, ampClient: AmpClient) -> None:
        self.ampClient = ampClient
        self.ampDatasetName = 'edgeandnode/uniswap_v3_base@0.0.1'

    async def get_pool_swaps(self, poolAddress: str, hoursBack: int = 24) -> list[SwapEvent]:
        cutoffTime = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(hours=hoursBack)
        timestampCutoff = cutoffTime.strftime('%Y-%m-%d %H:%M:%S')
        sql = f"""
        SELECT
            block_num,
            timestamp,
            tx_hash,
            log_index,
            event
        FROM "{self.ampDatasetName}".event__swap
        WHERE
            pool_address = {poolAddress}
            AND timestamp > TIMESTAMP '{timestampCutoff}'
        ORDER BY timestamp DESC
        LIMIT 10000
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

    async def get_pool_volatility(self, poolAddress: str, hoursBack: int = 24) -> float:
        cutoffTime = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(hours=hoursBack)
        timestampCutoff = cutoffTime.strftime('%Y-%m-%d %H:%M:%S')
        sql = f"""
        WITH prices AS (
            SELECT
                timestamp,
                POWER(CAST(event."sqrtPriceX96" AS DOUBLE) / 79228162514264337593543950336.0, 2) as price
            FROM "{self.ampDatasetName}".event__swap
            WHERE
                pool_address = {poolAddress}
                AND timestamp > TIMESTAMP '{timestampCutoff}'
        ),
        returns AS (
            SELECT
                timestamp,
                LN(price / LAG(price) OVER (ORDER BY timestamp)) as log_return
            FROM prices
        )
        SELECT
            STDDEV(log_return) as std_dev,
            COUNT(*) as count,
            EXTRACT(EPOCH FROM MAX(timestamp)) - EXTRACT(EPOCH FROM MIN(timestamp)) as duration_seconds
        FROM returns
        WHERE log_return IS NOT NULL
        """
        results = [row async for row in self.ampClient.execute_sql(sql)]
        if not results or results[0].get('std_dev') is None:
            return 0.0
        row = results[0]
        stdDev = float(cast(float, row['std_dev']))
        durationSeconds = int(cast(float, row['duration_seconds']))
        count = int(cast(int, row['count']))
        if durationSeconds <= 0 or count < MIN_DATA_POINTS:
            return 0.0
        swapsPerYear = (count / durationSeconds) * (365 * 24 * 3600)
        annualizedVol: float = stdDev * math.sqrt(swapsPerYear)
        return annualizedVol

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
