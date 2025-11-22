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
