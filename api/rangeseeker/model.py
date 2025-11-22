from __future__ import annotations

import datetime

from core.util.typing_util import JsonObject
from pydantic import BaseModel


class User(BaseModel):
    userId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    username: str


class UserWallet(BaseModel):
    userWalletId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    userId: str
    walletAddress: str


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


class Agent(BaseModel):
    agentId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    userId: str
    strategyId: str
    name: str
    emoji: str


class AgentWallet(BaseModel):
    agentWalletId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    agentId: str
    walletAddress: str
    delegatedSmartWallet: str | None


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
