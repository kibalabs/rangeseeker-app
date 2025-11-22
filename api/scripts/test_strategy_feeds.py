# ruff: noqa: T201

import asyncio
import datetime
import json
import math
import os
import statistics
from dataclasses import dataclass
from typing import cast

from core.exceptions import KibaException
from core.requester import Requester

import _path_fix  # type: ignore[import-not-found] # noqa: F401
from rangeseeker.amp_client import AmpClient
from rangeseeker.amp_client import SqlValue
from rangeseeker.gemini_llm import GeminiLLM

# Hardcoded pool configuration (WETH/USDC 0.05% on Base)
POOL_ADDRESS = '0xd0b53D9277642d899DF5C87A3966A349A798F224'
CHAIN_ID = 8453  # Base
BASE_ASSET = 'WETH'
QUOTE_ASSET = 'USDC'
WETH_ADDRESS = '0x4200000000000000000000000000000000000006'
USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

MIN_DATA_POINTS = 2

# Natural language strategy input (simulating user input)
STRATEGY_INPUT = 'I want tight range fee farming but widen if volatility spikes, and exit entirely to USDC if ETH ever drops below $3000'

# Configuration
AMP_TOKEN = os.environ['THEGRAPHAMP_API_KEY']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']

# Pyth Network configuration
PYTH_ETH_USD_PRICE_ID = '0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace'
PYTH_WS_URL = 'wss://hermes.pyth.network/ws'


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
        LIMIT 1000
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
        annualizedVol = stdDev * math.sqrt(swapsPerYear)
        return float(annualizedVol)

    async def get_current_price(self, poolAddress: str, token0Decimals: int = 18, token1Decimals: int = 6) -> float:
        state = await self.get_pool_current_state(poolAddress)
        if not state:
            return 0.0
        return self.calculate_price_from_sqrt_price_x96(state.sqrtPriceX96, token0Decimals, token1Decimals)

    def calculate_price_from_sqrt_price_x96(self, sqrtPriceX96: int, token0Decimals: int = 18, token1Decimals: int = 6) -> float:
        sqrtPrice = sqrtPriceX96 / (2**96)
        price = sqrtPrice**2
        adjustedPrice = price * (10**token0Decimals) / (10**token1Decimals)
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


class StrategyParser:
    def __init__(self, llm: GeminiLLM) -> None:
        self.llm = llm

    async def parse(self, description: str, contextData: dict[str, float | str | None]) -> dict:  # type: ignore[type-arg]
        systemPrompt = """You are a DeFi strategy analyzer that converts natural language descriptions into structured Uniswap V3 liquidity provision rules.

Current market context:
- Pool: WETH/USDC 0.05% on Base
- Current Price: {currentPrice} USDC per WETH
- 24h Volatility: {volatility}%

You must output a JSON object with this exact structure:
{{
  "rules": [
    {{
      "type": "RANGE_WIDTH",
      "priority": 3,
      "parameters": {{
        "baseRangePercent": 2.0,
        "dynamicWidening": null,
        "rebalanceBuffer": 0.1
      }}
    }},
    {{
      "type": "PRICE_THRESHOLD",
      "priority": 1,
      "parameters": {{
        "asset": "WETH",
        "operator": "LESS_THAN" | "GREATER_THAN",
        "priceUsd": 3000.0,
        "action": "EXIT_TO_STABLE",
        "targetAsset": "USDC"
      }}
    }},
    {{
      "type": "VOLATILITY_TRIGGER",
      "priority": 2,
      "parameters": {{
        "threshold": 0.05,
        "window": "24h",
        "action": "PAUSE_REBALANCING"
      }}
    }}
  ],
  "feedRequirements": ["PYTH_PRICE", "THEGRAPH_VOLATILITY"]
}}

Rule types:
- RANGE_WIDTH: Controls how tight/wide the liquidity range is (±% from current price). Priority 3.
  * baseRangePercent: 2.0 for tight, 5.0 for medium, 10.0 for wide
  * dynamicWidening: null or object with enabled, volatilityThreshold, widenToPercent
  * rebalanceBuffer: typically 0.1 (rebalance when 10% outside range)
  * Requires feed: PYTH_PRICE

- PRICE_THRESHOLD: Trigger when price crosses a specific value. Priority 1 (highest).
  * asset: "WETH"
  * operator: "LESS_THAN" or "GREATER_THAN"
  * priceUsd: numeric threshold
  * action: "EXIT_TO_STABLE" to exit position
  * targetAsset: "USDC"
  * Requires feed: PYTH_PRICE

- VOLATILITY_TRIGGER: React to market volatility changes. Priority 2.
  * threshold: decimal (e.g., 0.05 for 5%)
  * window: "24h"
  * action: "PAUSE_REBALANCING" or other action
  * Requires feed: THEGRAPH_VOLATILITY

Feed requirements:
- PYTH_PRICE: Always needed for any price-based rule
- THEGRAPH_VOLATILITY: Needed for volatility-based rules

Parse the user's strategy and create appropriate rules with correct priorities. Be specific with numbers."""
        userPrompt = f'Parse this strategy: {description}'
        formattedSystemPrompt = systemPrompt.format(
            currentPrice=contextData.get('currentPrice', 0.0),
            volatility=contextData.get('volatility', 0.0) * 100,
        )
        promptQuery = await self.llm.get_query(systemPrompt=formattedSystemPrompt, prompt=userPrompt)
        parsed = await self.llm.get_next_step(promptQuery)
        if 'rules' not in parsed or not isinstance(parsed['rules'], list):
            raise KibaException('LLM response missing rules array')
        if 'summary' not in parsed:
            parsed['summary'] = self._generate_summary(parsed['rules'])
        return parsed

    def _generate_summary(self, rules: list) -> str:  # type: ignore[type-arg]
        summaryParts = []
        for rule in rules:
            if rule['type'] == 'RANGE_WIDTH':
                rangePercent = rule['parameters']['baseRangePercent']
                summaryParts.append(f'Maintain ±{rangePercent}% range')
                dynamicWidening = rule['parameters'].get('dynamicWidening')
                if dynamicWidening and isinstance(dynamicWidening, dict) and dynamicWidening.get('enabled'):
                    volThreshold = dynamicWidening['volatilityThreshold'] * 100
                    widenTo = dynamicWidening['widenToPercent']
                    summaryParts.append(f'widen to ±{widenTo}% if volatility > {volThreshold}%')
            elif rule['type'] == 'PRICE_THRESHOLD':
                asset = rule['parameters']['asset']
                operator = rule['parameters']['operator']
                price = rule['parameters']['priceUsd']
                action = rule['parameters']['action']
                opText = 'below' if operator == 'LESS_THAN' else 'above'
                actionText = f'exit to {rule["parameters"]["targetAsset"]}' if action == 'EXIT_TO_STABLE' else action.lower()
                summaryParts.append(f'{actionText} if {asset} {opText} ${price:,.0f}')
        return ', '.join(summaryParts)


async def main() -> None:
    print('=' * 80)
    print('RANGE SEEKER - STRATEGY FEEDS TEST')
    print('=' * 80)
    print()
    requester = Requester()
    ampClient = AmpClient(
        flightUrl='https://gateway.amp.staging.thegraph.com',
        token=AMP_TOKEN,
    )
    uniswapClient = UniswapDataClient(ampClient=ampClient)
    geminiLlm = GeminiLLM(apiKey=GEMINI_API_KEY, requester=requester)
    parser = StrategyParser(llm=geminiLlm)
    print(f'Pool: {BASE_ASSET}/{QUOTE_ASSET} ({POOL_ADDRESS})')
    print(f'Chain: Base (ChainID {CHAIN_ID})')
    print()
    print(f'User Input: "{STRATEGY_INPUT}"')
    print()
    print('-' * 80)
    print('STEP 1: FETCH CONTEXT DATA FROM THEGRAPH AMP (for UI display)')
    print('-' * 80)
    print()
    print('NOTE: TheGraph AMP provides SQL access to blockchain data via hosted datasets.')
    print(f'Dataset: {uniswapClient.ampDatasetName}')
    print('Available tables: blocks, transactions, logs (raw blockchain data)')
    print('Uniswap V3 data derived from logs table filtering by pool address')
    print()
    print('Fetching 24h swap data for volatility calculation...')
    currentPrice = await uniswapClient.get_current_price(POOL_ADDRESS)
    volatility = await uniswapClient.get_pool_volatility(POOL_ADDRESS, hoursBack=24)
    swapCount = 'aggregated'
    print(f'✓ Current Price: ${currentPrice:,.2f} USDC per WETH')
    print(f'✓ 24h Annualized Volatility: {volatility * 100:.2f}%')
    print()
    contextData: dict[str, float | str] = {
        'currentPrice': currentPrice,
        'volatility': volatility,
        'swapCount24h': swapCount,
    }
    print('-' * 80)
    print('STEP 2: PARSE STRATEGY WITH LLM')
    print('-' * 80)
    print()
    print('Sending to Gemini for parsing...')
    strategyDef = await parser.parse(STRATEGY_INPUT, contextData)
    print(f'✓ Parsed Strategy: {strategyDef.get("summary", "N/A")}')
    print(f'✓ Feed Requirements: {", ".join(strategyDef["feedRequirements"])}')
    print()
    print('Rules:')
    for i, rule in enumerate(strategyDef['rules'], 1):
        print(f'  {i}. {rule["type"]} (Priority {rule["priority"]})')
        print(f'     Parameters: {json.dumps(rule["parameters"], indent=8)}')
    print()
    print('-' * 80)
    print('STEP 3: MAP RULES TO FEEDS')
    print('-' * 80)
    print()
    feedMappings = []
    for rule in strategyDef['rules']:
        if rule['type'] == 'RANGE_WIDTH' or rule['type'] == 'PRICE_THRESHOLD':
            feedMappings.append(
                {
                    'ruleType': rule['type'],
                    'feedType': 'PYTH_PRICE',
                    'feedConfig': {
                        'priceId': PYTH_ETH_USD_PRICE_ID,
                        'wsUrl': PYTH_WS_URL,
                        'asset': BASE_ASSET,
                    },
                }
            )
        if rule['type'] == 'VOLATILITY_TRIGGER' or (rule['type'] == 'RANGE_WIDTH' and rule['parameters'].get('dynamicWidening')):
            feedMappings.append(
                {
                    'ruleType': rule['type'],
                    'feedType': 'THEGRAPH_VOLATILITY',
                    'feedConfig': {
                        'flightUrl': ampClient.flightUrl,
                        'dataset': uniswapClient.ampDatasetName,
                        'poolAddress': POOL_ADDRESS,
                        'windowHours': 24,
                    },
                }
            )
    print(f'Created {len(feedMappings)} feed mappings:')
    for mapping in feedMappings:
        print(f'  • {mapping["feedType"]} → {mapping["ruleType"]}')
        print(f'    Config: {json.dumps(mapping["feedConfig"], indent=10)}')
    print()
    print('-' * 80)
    print('STEP 4: SIMULATE RULE EVALUATION')
    print('-' * 80)
    print()
    print('This demonstrates how the agent would continuously evaluate rules:')
    print()
    simulatedPythPrice = currentPrice if currentPrice > 0 else 3500.0
    print(f'📡 PYTH_PRICE update: ETH = ${simulatedPythPrice:,.2f}')
    for rule in strategyDef['rules']:
        print(f'\nEvaluating {rule["type"]}...')
        if rule['type'] == 'RANGE_WIDTH':
            rangePercent = rule['parameters']['baseRangePercent']
            lowerBound = simulatedPythPrice * (1 - rangePercent / 100)
            upperBound = simulatedPythPrice * (1 + rangePercent / 100)
            print(f'  Current range: ${lowerBound:,.2f} - ${upperBound:,.2f}')
            dynamicWidening = rule['parameters'].get('dynamicWidening')
            if dynamicWidening and isinstance(dynamicWidening, dict) and dynamicWidening.get('enabled'):
                volThreshold = dynamicWidening['volatilityThreshold']
                if volatility > volThreshold:
                    widenToPercent = dynamicWidening['widenToPercent']
                    print(f'  ⚠ Volatility {volatility * 100:.2f}% > threshold {volThreshold * 100:.2f}%')
                    print(f'  → Widening range to ±{widenToPercent}%')
                else:
                    print(f'  ✓ Volatility {volatility * 100:.2f}% within threshold')
        elif rule['type'] == 'PRICE_THRESHOLD':
            targetPrice = rule['parameters']['priceUsd']
            operator = rule['parameters']['operator']
            action = rule['parameters']['action']
            if operator == 'LESS_THAN':
                triggered = simulatedPythPrice < targetPrice
                comparison = '<'
            else:
                triggered = simulatedPythPrice > targetPrice
                comparison = '>'
            if triggered:
                print(f'  🚨 TRIGGERED: ${simulatedPythPrice:,.2f} {comparison} ${targetPrice:,.2f}')
                print(f'  → Action: {action}')
            else:
                print(f'  ✓ Not triggered: ${simulatedPythPrice:,.2f} vs ${targetPrice:,.2f}')
        elif rule['type'] == 'VOLATILITY_TRIGGER':
            threshold = rule['parameters']['threshold']
            action = rule['parameters']['action']
            if volatility > threshold:
                print(f'  🚨 TRIGGERED: Volatility {volatility * 100:.2f}% > {threshold * 100:.2f}%')
                print(f'  → Action: {action}')
            else:
                print(f'  ✓ Not triggered: Volatility {volatility * 100:.2f}% within threshold')
    print()
    print('=' * 80)
    print('TEST COMPLETE')
    print('=' * 80)
    print()
    print('Summary:')
    print(f'  • Fetched real blockchain data from TheGraph AMP')
    print(f'  • Parsed strategy with Gemini LLM')
    print(f'  • Mapped {len(feedMappings)} feed subscriptions')
    print(f'  • Evaluated {len(strategyDef["rules"])} rules')
    print()
    print('Next Steps:')
    print('  1. Integrate this flow into main app')
    print('  2. Set up Pyth WebSocket subscription for real-time price updates')
    print('  3. Schedule periodic AMP queries for volatility recalculation')
    print('  4. Implement rule evaluation engine in agent manager')
    print()


if __name__ == '__main__':
    asyncio.run(main())
