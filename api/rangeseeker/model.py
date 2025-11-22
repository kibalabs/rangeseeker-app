from __future__ import annotations

import datetime

from pydantic import BaseModel

from core.util.typing_util import JsonObject


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
