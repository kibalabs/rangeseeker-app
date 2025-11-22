import datetime

from pydantic import BaseModel


class AuthToken(BaseModel):
    message: str
    signature: str


class User(BaseModel):
    userId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    username: str
