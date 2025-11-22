import datetime

from pydantic import BaseModel


class User(BaseModel):
    userId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    username: str
