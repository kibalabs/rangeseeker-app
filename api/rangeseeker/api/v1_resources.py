import datetime

from core.util.typing_util import JsonObject
from pydantic import BaseModel


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
    volatility7d: float
    volatilityAnnualized: float
    volatilityRealized: float
    feeGrowth7d: float
    feeRate: float


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
    rulesJson: list[JsonObject]
    feedRequirements: list[str]
    summary: str


class Agent(BaseModel):
    agentId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    userId: str
    strategyId: str
    name: str
    emoji: str


class CreateAgentRequest(BaseModel):
    name: str
    emoji: str
    strategyId: str


class Asset(BaseModel):
    assetId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    chainId: int
    address: str
    name: str
    symbol: str
    decimals: int


class AssetPrice(BaseModel):
    assetPriceId: int
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    assetId: str
    priceUsd: float
    date: datetime.datetime


class AssetBalance(BaseModel):
    asset: Asset
    assetPrice: AssetPrice
    balance: int


class Wallet(BaseModel):
    walletAddress: str
    assetBalances: list[AssetBalance]
    delegatedSmartWallet: str | None


class PreviewDeposit(BaseModel):
    swapDescription: str
    depositDescription: str
    token0Amount: float
    token1Amount: float
    token0Symbol: str
    token1Symbol: str
