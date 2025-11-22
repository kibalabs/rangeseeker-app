# ruff: noqa: T201

import asyncio
import datetime
import json
import math
import os
import statistics
from typing import Any

from core.requester import Requester

import _path_fix  # noqa: F401
from rangeseeker.amp_client import AmpClient

# Hardcoded pool configuration (WETH/USDC 0.05% on Base)
POOL_ADDRESS = '0xd0b53D9277642d899DF5C87A3966A349A798F224'
CHAIN_ID = 8453  # Base
BASE_ASSET = 'WETH'
QUOTE_ASSET = 'USDC'
WETH_ADDRESS = '0x4200000000000000000000000000000000000006'
USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

# Natural language strategy input (simulating user input)
STRATEGY_INPUT = 'I want tight range fee farming but widen if volatility spikes, and exit entirely to USDC if ETH ever drops below $3000'

# Configuration
AMP_TOKEN = os.environ['THEGRAPHAMP_API_KEY']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
UNISWAP_DATASET = 'edgeandnode/uniswap_v3_base@0.0.1'

# Pyth Network configuration
PYTH_ETH_USD_PRICE_ID = '0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace'
PYTH_WS_URL = 'wss://hermes.pyth.network/ws'


class UniswapDataClient:
    """Client for querying Uniswap V3 pool data from TheGraph AMP."""

    def __init__(self, ampClient: AmpClient, dataset: str) -> None:
        self.ampClient = ampClient
        self.dataset = dataset

    async def get_pool_swaps(self, poolAddress: str, hoursBack: int = 24) -> list[dict[str, Any]]:
        """Fetch recent swaps for a pool from Uniswap V3 Swap events."""
        cutoffTime = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(hours=hoursBack)
        timestampCutoff = cutoffTime.strftime('%Y-%m-%d %H:%M:%S')

        sql = f"""
        SELECT
            block_num,
            timestamp,
            tx_hash,
            log_index,
            event
        FROM "{self.dataset}".event__swap
        WHERE
            pool_address = decode(SUBSTRING(LOWER('{poolAddress}'), 3), 'hex')
            AND timestamp > TIMESTAMP '{timestampCutoff}'
        ORDER BY timestamp DESC
        LIMIT 1000
        """

        results = []
        async for row in self.ampClient.execute_sql(sql):
            results.append(row)
        return results

    async def get_pool_current_state(self, poolAddress: str) -> dict[str, Any] | None:
        """Get most recent state from pool by querying latest Swap event."""
        sql = f"""
        SELECT
            block_num,
            timestamp,
            event
        FROM "{self.dataset}".event__swap
        WHERE
            pool_address = decode(SUBSTRING(LOWER('{poolAddress}'), 3), 'hex')
        ORDER BY block_num DESC
        LIMIT 1
        """

        results = []
        async for row in self.ampClient.execute_sql(sql):
            results.append(row)
        return results[0] if results else None

    def decode_swap_event(self, log: dict[str, Any]) -> dict[str, Any]:
        """Extract Uniswap V3 Swap event data from pre-built event table."""
        event = log.get('event', {})
        return {
            'timestamp': log.get('timestamp', 0),
            'sqrtPriceX96': str(event.get('sqrtPriceX96', 0)),
            'amount0': str(event.get('amount0', 0)),
            'amount1': str(event.get('amount1', 0)),
            'liquidity': str(event.get('liquidity', 0)),
            'tick': str(event.get('tick', 0)),
        }

    def calculate_price_from_sqrt_price_x96(self, sqrtPriceX96: str, token0Decimals: int = 18, token1Decimals: int = 6) -> float:
        """Convert Uniswap V3 sqrtPriceX96 to human-readable price."""
        sqrtPrice = int(sqrtPriceX96) / (2**96)
        price = sqrtPrice**2
        adjustedPrice = price * (10**token0Decimals) / (10**token1Decimals)
        return adjustedPrice

    def calculate_volatility(self, swaps: list[dict[str, Any]]) -> float:
        """Calculate implied volatility from price movements (annualized)."""
        if len(swaps) < 2:
            return 0.0

        # Extract prices from sqrtPriceX96
        prices = []
        for swap in swaps:
            price = self.calculate_price_from_sqrt_price_x96(swap['sqrtPriceX96'])
            if price > 0:
                prices.append(price)

        if len(prices) < 2:
            return 0.0

        prices.reverse()  # Chronological order

        # Calculate log returns
        logReturns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices)) if prices[i - 1] > 0]

        if not logReturns:
            return 0.0

        # Standard deviation of log returns
        stdDev = statistics.stdev(logReturns) if len(logReturns) > 1 else 0.0

        # Annualize (assuming swaps are roughly evenly distributed over the time period)
        timeSpanHours = (int(swaps[0]['timestamp']) - int(swaps[-1]['timestamp'])) / 3600
        if timeSpanHours <= 0:
            return 0.0

        swapsPerHour = len(swaps) / timeSpanHours
        # Approximate annualization factor
        annualizationFactor = math.sqrt(swapsPerHour * 24 * 365)
        annualizedVol = stdDev * annualizationFactor

        return annualizedVol


class StrategyParser:
    """Parse natural language strategy descriptions into structured rule definitions using LLM."""

    def __init__(self, requester: Requester, apiKey: str, modelId: str = 'gemini-2.0-flash-exp') -> None:
        self.requester = requester
        self.apiKey = apiKey
        self.modelId = modelId
        self.endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{modelId}:generateContent'

    async def parse(self, description: str, contextData: dict[str, Any]) -> dict[str, Any]:
        """
        Parse natural language strategy into structured rules.

        Args:
            description: User's natural language strategy description
            contextData: Current market context (price, volatility, etc.) to inform parsing

        Returns:
            Dict with "rules", "feedRequirements", and "summary"
        """
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

        headers = {
            'Content-Type': 'application/json',
        }

        payload = {
            'system_instruction': {'parts': [{'text': formattedSystemPrompt}]},
            'contents': [{'role': 'user', 'parts': [{'text': userPrompt}]}],
            'generationConfig': {
                'temperature': 0.3,
                'responseMimeType': 'application/json',
            },
        }

        response = await self.requester.post(
            url=f'{self.endpoint}?key={self.apiKey}',
            dataDict=payload,
            headers=headers,
            timeout=30,
        )

        data = response.json()

        if 'error' in data:
            raise Exception(f'Gemini API error: {data["error"]}')

        rawText = data['candidates'][0]['content']['parts'][0]['text']
        # Gemini sometimes wraps JSON in markdown code blocks
        jsonText = rawText.replace('```json', '', 1).replace('```', '', 1).strip()
        parsed = json.loads(jsonText)

        # Validate structure
        if 'rules' not in parsed or not isinstance(parsed['rules'], list):
            raise Exception('LLM response missing rules array')

        # Add summary if not present
        if 'summary' not in parsed:
            parsed['summary'] = self._generate_summary(parsed['rules'])

        return parsed

    def _generate_summary(self, rules: list[dict[str, Any]]) -> str:
        """Generate human-readable summary of strategy rules."""
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
    """Main script execution."""
    print('=' * 80)
    print('RANGE SEEKER - STRATEGY FEEDS TEST')
    print('=' * 80)
    print()

    # Initialize clients
    requester = Requester()
    ampClient = AmpClient(
        flightUrl='https://gateway.amp.staging.thegraph.com',
        token=AMP_TOKEN,
    )
    uniswapClient = UniswapDataClient(ampClient=ampClient, dataset=UNISWAP_DATASET)
    parser = StrategyParser(requester, GEMINI_API_KEY)

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
    print(f'Dataset: {uniswapClient.dataset}')
    print('Available tables: blocks, transactions, logs (raw blockchain data)')
    print('Uniswap V3 data derived from logs table filtering by pool address')
    print()

    # Fetch recent swaps for volatility calculation
    print('Fetching 24h swap data for volatility calculation...')
    swaps = await uniswapClient.get_pool_swaps(POOL_ADDRESS, hoursBack=24)
    print(f'✓ Found {len(swaps)} swaps in last 24h')

    if not swaps:
        print('⚠ No swap data available. Cannot calculate volatility.')
        volatility = 0.0
        currentPrice = 0.0
    else:
        # Decode swap events
        decodedSwaps = [uniswapClient.decode_swap_event(swap) for swap in swaps]

        # Calculate current price from most recent swap
        latestSwap = decodedSwaps[0]
        currentPrice = uniswapClient.calculate_price_from_sqrt_price_x96(latestSwap['sqrtPriceX96'])

        # Calculate volatility
        volatility = uniswapClient.calculate_volatility(decodedSwaps)

        print(f'✓ Current Price: ${currentPrice:,.2f} USDC per WETH')
        print(f'✓ 24h Annualized Volatility: {volatility * 100:.2f}%')

    print()

    # Build context data for strategy parsing
    contextData = {
        'currentPrice': currentPrice,
        'volatility': volatility,
        'swapCount24h': len(swaps),
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
                        'dataset': uniswapClient.dataset,
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

    # Simulate real-time price update from Pyth
    simulatedPythPrice = currentPrice if currentPrice > 0 else 3500.0
    print(f'📡 PYTH_PRICE update: ETH = ${simulatedPythPrice:,.2f}')

    # Evaluate each rule
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
