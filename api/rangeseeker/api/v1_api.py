import typing

from core.api.api_request import KibaApiRequest
from core.api.json_route import json_route
from core.http.basic_authentication import BasicAuthentication
from starlette.routing import Route

from rangeseeker.api import v1_endpoints as endpoints
from rangeseeker.api import v1_resources as resources
from rangeseeker.api.authorizer import authorize_signature
from rangeseeker.app_manager import AppManager
from rangeseeker.strategy_parser import StrategyDefinition as ParserStrategyDefinition


def create_v1_routes(appManager: AppManager) -> list[Route]:
    @json_route(requestType=endpoints.LoginWithWalletRequest, responseType=endpoints.LoginWithWalletResponse)
    @authorize_signature(authorizer=appManager)
    async def user_login_with_wallet_address(request: KibaApiRequest[endpoints.LoginWithWalletRequest]) -> endpoints.LoginWithWalletResponse:
        user = await appManager.user_login_with_wallet_address(walletAddress=request.data.walletAddress, userId=typing.cast(BasicAuthentication, request.authBasic).username)
        return endpoints.LoginWithWalletResponse(user=resources.User.model_validate(user.model_dump()))

    @json_route(requestType=endpoints.CreateUserRequest, responseType=endpoints.CreateUserResponse)
    async def create_user(request: KibaApiRequest[endpoints.CreateUserRequest]) -> endpoints.CreateUserResponse:
        user = await appManager.create_user(walletAddress=request.data.walletAddress, username=request.data.username)
        return endpoints.CreateUserResponse(user=resources.User.model_validate(user.model_dump()))

    @json_route(requestType=endpoints.ParseStrategyRequest, responseType=endpoints.ParseStrategyResponse)
    @authorize_signature(authorizer=appManager)
    async def parse_strategy(request: KibaApiRequest[endpoints.ParseStrategyRequest]) -> endpoints.ParseStrategyResponse:
        strategyDefinition = await appManager.parse_strategy(description=request.data.description)
        return endpoints.ParseStrategyResponse(strategyDefinition=resources.StrategyDefinition.model_validate(strategyDefinition.model_dump()))

    @json_route(requestType=endpoints.GetPoolDataRequest, responseType=endpoints.GetPoolDataResponse)
    async def get_pool_data(request: KibaApiRequest[endpoints.GetPoolDataRequest]) -> endpoints.GetPoolDataResponse:
        poolData = await appManager.get_pool_data(chainId=request.data.chainId, token0Address=request.data.token0Address, token1Address=request.data.token1Address)
        return endpoints.GetPoolDataResponse(poolData=resources.PoolData.model_validate(poolData))

    @json_route(requestType=endpoints.GetPoolHistoricalDataRequest, responseType=endpoints.GetPoolHistoricalDataResponse)
    async def get_pool_historical_data(request: KibaApiRequest[endpoints.GetPoolHistoricalDataRequest]) -> endpoints.GetPoolHistoricalDataResponse:
        poolHistoricalData = await appManager.get_pool_historical_data(chainId=request.data.chainId, token0Address=request.data.token0Address, token1Address=request.data.token1Address, hoursBack=request.data.hoursBack)
        return endpoints.GetPoolHistoricalDataResponse(poolHistoricalData=resources.PoolHistoricalData.model_validate(poolHistoricalData))

    @json_route(requestType=endpoints.EmptyRequest, responseType=endpoints.ListAgentsResponse)
    @authorize_signature(authorizer=appManager)
    async def list_agents(request: KibaApiRequest[endpoints.EmptyRequest]) -> endpoints.ListAgentsResponse:
        agents = await appManager.list_agents(userId=typing.cast(BasicAuthentication, request.authBasic).username)
        return endpoints.ListAgentsResponse(agents=[resources.Agent.model_validate(agent.model_dump()) for agent in agents])

    @json_route(requestType=endpoints.CreateAgentRequest, responseType=endpoints.CreateAgentResponse)
    @authorize_signature(authorizer=appManager)
    async def create_agent(request: KibaApiRequest[endpoints.CreateAgentRequest]) -> endpoints.CreateAgentResponse:
        agent = await appManager.create_agent(
            userId=typing.cast(BasicAuthentication, request.authBasic).username,
            name=request.data.name,
            emoji=request.data.emoji,
            strategyName=request.data.strategyName,
            strategyDescription=request.data.strategyDescription,
            strategyDefinition=ParserStrategyDefinition.model_validate(request.data.strategyDefinition.model_dump())
        )
        return endpoints.CreateAgentResponse(agent=resources.Agent.model_validate(agent.model_dump()))

    @json_route(requestType=endpoints.GetAgentRequest, responseType=endpoints.GetAgentResponse)
    @authorize_signature(authorizer=appManager)
    async def get_agent(request: KibaApiRequest[endpoints.GetAgentRequest]) -> endpoints.GetAgentResponse:
        agent = await appManager.get_agent(userId=typing.cast(BasicAuthentication, request.authBasic).username, agentId=request.data.agentId)
        return endpoints.GetAgentResponse(agent=resources.Agent.model_validate(agent.model_dump()))

    @json_route(requestType=endpoints.GetAgentWalletRequest, responseType=endpoints.GetAgentWalletResponse)
    @authorize_signature(authorizer=appManager)
    async def get_agent_wallet(request: KibaApiRequest[endpoints.GetAgentWalletRequest]) -> endpoints.GetAgentWalletResponse:
        wallet = await appManager.get_agent_wallet(userId=typing.cast(BasicAuthentication, request.authBasic).username, agentId=request.data.agentId)
        return endpoints.GetAgentWalletResponse(wallet=resources.Wallet.model_validate(wallet.model_dump()))

    return [
        Route('/users/login-with-wallet', user_login_with_wallet_address, methods=['POST']),
        Route('/users', create_user, methods=['POST']),
        Route('/strategies/parse', parse_strategy, methods=['POST']),
        Route('/pools', get_pool_data, methods=['GET']),
        Route('/pools/historical-data', get_pool_historical_data, methods=['GET']),
        Route('/agents', list_agents, methods=['GET']),
        Route('/agents', create_agent, methods=['POST']),
        Route('/agents/{agentId}', get_agent, methods=['GET']),
        Route('/agents/{agentId}/wallet', get_agent_wallet, methods=['GET']),
    ]
