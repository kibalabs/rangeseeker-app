import datetime

from pydantic import BaseModel

from core.util.typing_util import JsonObject


class AuthToken(BaseModel):
    message: str
    signature: str


class User(BaseModel):
    userId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    username: str


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


class PoolData(BaseModel):
    chainId: int
    token0Address: str
    token1Address: str
    poolAddress: str
    currentPrice: float
    volatility24h: float


class PricePoint(BaseModel):
    timestamp: int
    price: float


class PoolHistoricalData(BaseModel):
    chainId: int
    token0Address: str
    token1Address: str
    poolAddress: str
    pricePoints: list[PricePoint]


class Strategy(BaseModel):
    strategyId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    userId: str
    name: str
    description: str
    rulesJson: JsonObject
    feedRequirements: list[str]
    summary: str
