from __future__ import annotations

import datetime

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
