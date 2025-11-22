from pydantic import BaseModel

from rangeseeker.api import v1_resources as resources


class LoginWithWalletRequest(BaseModel):
    walletAddress: str


class LoginWithWalletResponse(BaseModel):
    user: resources.User


class CreateUserRequest(BaseModel):
    walletAddress: str
    username: str


class CreateUserResponse(BaseModel):
    user: resources.User
