from typing import cast

from core.exceptions import KibaException
from core.util.typing_util import JsonObject
from pydantic import BaseModel

from rangeseeker.external.gemini_llm import GeminiLLM


class DynamicWidening(BaseModel):
    enabled: bool
    volatilityThreshold: float
    widenToPercent: float


class RangeWidthParameters(BaseModel):
    baseRangePercent: float
    dynamicWidening: DynamicWidening | None
    rebalanceBuffer: float


class PriceThresholdParameters(BaseModel):
    asset: str
    operator: str
    priceUsd: float
    action: str
    targetAsset: str


class VolatilityTriggerParameters(BaseModel):
    threshold: float
    window: str
    action: str


class StrategyRule(BaseModel):
    type: str
    priority: int
    parameters: RangeWidthParameters | PriceThresholdParameters | VolatilityTriggerParameters


class StrategyDefinition(BaseModel):
    rules: list[StrategyRule]
    feedRequirements: list[str]
    summary: str


class StrategyParser:
    def __init__(self, llm: GeminiLLM) -> None:
        self.llm = llm

    async def parse(self, description: str, contextData: dict[str, float | str | None]) -> StrategyDefinition:
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
            volatility=cast(float, contextData.get('volatility', 0.0)) * 100,
        )
        promptQuery = await self.llm.get_query(systemPrompt=formattedSystemPrompt, prompt=userPrompt)
        parsed = await self.llm.get_next_step(promptQuery)
        if 'rules' not in parsed or not isinstance(parsed['rules'], list):
            raise KibaException('LLM response missing rules array')
        rules = [self._parse_rule(cast(JsonObject, ruleDict)) for ruleDict in parsed['rules']]
        feedRequirements = [str(req) for req in cast(list[str], parsed.get('feedRequirements', []))]
        summary = str(parsed.get('summary', self._generate_summary(rules)))
        return StrategyDefinition(rules=rules, feedRequirements=feedRequirements, summary=summary)

    def _parse_rule(self, ruleDict: JsonObject) -> StrategyRule:
        ruleType = str(ruleDict['type'])
        priority = int(cast(int, ruleDict['priority']))
        paramsDict = cast(JsonObject, ruleDict['parameters'])
        parameters: RangeWidthParameters | PriceThresholdParameters | VolatilityTriggerParameters
        if ruleType == 'RANGE_WIDTH':
            dynamicWideningDict = paramsDict.get('dynamicWidening')
            dynamicWidening = None
            if dynamicWideningDict and isinstance(dynamicWideningDict, dict):
                dynamicWidening = DynamicWidening(
                    enabled=bool(dynamicWideningDict.get('enabled', False)),
                    volatilityThreshold=float(cast(float, dynamicWideningDict.get('volatilityThreshold', 0.0))),
                    widenToPercent=float(cast(float, dynamicWideningDict.get('widenToPercent', 0.0))),
                )
            parameters = RangeWidthParameters(
                baseRangePercent=float(cast(float, paramsDict['baseRangePercent'])),
                dynamicWidening=dynamicWidening,
                rebalanceBuffer=float(cast(float, paramsDict.get('rebalanceBuffer', 0.1))),
            )
        elif ruleType == 'PRICE_THRESHOLD':
            parameters = PriceThresholdParameters(
                asset=str(paramsDict['asset']),
                operator=str(paramsDict['operator']),
                priceUsd=float(cast(float, paramsDict['priceUsd'])),
                action=str(paramsDict['action']),
                targetAsset=str(paramsDict['targetAsset']),
            )
        elif ruleType == 'VOLATILITY_TRIGGER':
            parameters = VolatilityTriggerParameters(
                threshold=float(cast(float, paramsDict['threshold'])),
                window=str(paramsDict['window']),
                action=str(paramsDict['action']),
            )
        else:
            raise KibaException(f'Unknown rule type: {ruleType}')
        return StrategyRule(type=ruleType, priority=priority, parameters=parameters)

    def _generate_summary(self, rules: list[StrategyRule]) -> str:
        summaryParts = []
        for rule in rules:
            if rule.type == 'RANGE_WIDTH':
                rangeParams = cast(RangeWidthParameters, rule.parameters)
                summaryParts.append(f'Maintain ±{rangeParams.baseRangePercent}% range')
                if rangeParams.dynamicWidening and rangeParams.dynamicWidening.enabled:
                    volThreshold = rangeParams.dynamicWidening.volatilityThreshold * 100
                    widenTo = rangeParams.dynamicWidening.widenToPercent
                    summaryParts.append(f'widen to ±{widenTo}% if volatility > {volThreshold}%')
            elif rule.type == 'PRICE_THRESHOLD':
                priceParams = cast(PriceThresholdParameters, rule.parameters)
                opText = 'below' if priceParams.operator == 'LESS_THAN' else 'above'
                actionText = f'exit to {priceParams.targetAsset}' if priceParams.action == 'EXIT_TO_STABLE' else priceParams.action.lower()
                summaryParts.append(f'{actionText} if {priceParams.asset} {opText} ${priceParams.priceUsd:,.0f}')
        return ', '.join(summaryParts)
