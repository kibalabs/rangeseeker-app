from core.api.api_request import KibaApiRequest
from core.api.json_route import json_route
from core.exceptions import NotFoundException
from starlette.routing import Route

from rangeseeker.api import v1_endpoints as endpoints
from rangeseeker.api import v1_resources as resources
from rangeseeker.app_manager import AppManager


def create_v1_routes(appManager: AppManager) -> list[Route]:
    @json_route(requestType=endpoints.LoginWithWalletRequest, responseType=endpoints.LoginWithWalletResponse)
    async def user_login_with_wallet_address(request: KibaApiRequest[endpoints.LoginWithWalletRequest]) -> endpoints.LoginWithWalletResponse:
        try:
            user = await appManager.get_user_by_wallet_address(walletAddress=request.data.walletAddress)
            return endpoints.LoginWithWalletResponse(user=resources.User.model_validate(user.model_dump()))
        except NotFoundException:
            return endpoints.LoginWithWalletResponse(user=None)

    @json_route(requestType=endpoints.CreateUserRequest, responseType=endpoints.CreateUserResponse)
    async def create_user(request: KibaApiRequest[endpoints.CreateUserRequest]) -> endpoints.CreateUserResponse:
        user = await appManager.create_user(walletAddress=request.data.walletAddress, username=request.data.username)
        return endpoints.CreateUserResponse(user=resources.User.model_validate(user.model_dump()))

    return [
        Route('/users/login-with-wallet', user_login_with_wallet_address, methods=['POST']),
        Route('/users', create_user, methods=['POST']),
    ]
