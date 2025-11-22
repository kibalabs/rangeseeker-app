from pydantic import BaseModel

from rangeseeker.api import v1_resources as resources


class EmptyRequest(BaseModel):
    pass


class LoginWithWalletRequest(BaseModel):
    walletAddress: str


class LoginWithWalletResponse(BaseModel):
    user: resources.User


class CreateUserRequest(BaseModel):
    walletAddress: str
    username: str


class CreateUserResponse(BaseModel):
    user: resources.User


class ParseStrategyRequest(BaseModel):
    description: str


class ParseStrategyResponse(BaseModel):
    strategyDefinition: resources.StrategyDefinition


class GetPoolDataRequest(BaseModel):
    chainId: int
    token0Address: str
    token1Address: str


class GetPoolDataResponse(BaseModel):
    poolData: resources.PoolData


class GetPoolHistoricalDataRequest(BaseModel):
    chainId: int
    token0Address: str
    token1Address: str
    hoursBack: int


class GetPoolHistoricalDataResponse(BaseModel):
    poolHistoricalData: resources.PoolHistoricalData


class CreateStrategyRequest(BaseModel):
    name: str
    description: str
    strategyDefinition: resources.StrategyDefinition


class CreateStrategyResponse(BaseModel):
    strategy: resources.Strategy


class GetStrategyResponse(BaseModel):
    strategy: resources.Strategy


class ListUserStrategiesResponse(BaseModel):
    strategies: list[resources.Strategy]


class ListAgentsResponse(BaseModel):
    agents: list[resources.Agent]


class CreateAgentRequest(BaseModel):
    name: str
    emoji: str
    strategyName: str
    strategyDescription: str
    strategyDefinition: resources.StrategyDefinition


class CreateAgentResponse(BaseModel):
    agent: resources.Agent


class GetAgentRequest(BaseModel):
    agentId: str


class GetAgentResponse(BaseModel):
    agent: resources.Agent


class GetAgentWalletRequest(BaseModel):
    agentId: str


class GetAgentWalletResponse(BaseModel):
    wallet: resources.Wallet
