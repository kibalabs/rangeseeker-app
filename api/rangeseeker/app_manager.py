import base64

from core.exceptions import ForbiddenException
from core.exceptions import NotFoundException
from core.exceptions import UnauthorizedException
from core.store.database import Database
from core.util import chain_util
from eth_account.messages import encode_defunct
from siwe import SiweMessage  # type: ignore[import-untyped]
from web3 import Web3

from rangeseeker.api.authorizer import Authorizer
from rangeseeker.api.v1_resources import AuthToken
from rangeseeker.model import User
from rangeseeker.model import UserWallet
from rangeseeker.user_manager import UserManager

w3 = Web3()


class AppManager(Authorizer):
    def __init__(self, database: Database, userManager: UserManager) -> None:
        self.database = database
        self.userManager = userManager
        self._signatureSignerMap: dict[str, str] = {}

    async def _retrieve_signature_signer_address(self, signatureString: str) -> str:
        if signatureString in self._signatureSignerMap:
            return self._signatureSignerMap[signatureString]
        authTokenJson = base64.b64decode(signatureString).decode('utf-8')
        authToken = AuthToken.model_validate_json(authTokenJson)
        messageHash = encode_defunct(text=authToken.message)
        siweMessage = SiweMessage.from_message(message=authToken.message)
        signerId = chain_util.normalize_address(siweMessage.address)
        messageSignerId = chain_util.normalize_address(w3.eth.account.recover_message(messageHash, signature=authToken.signature))
        if messageSignerId != signerId:
            raise UnauthorizedException
        self._signatureSignerMap[signatureString] = signerId
        return signerId

    async def retrieve_signature_signer(self, signatureString: str) -> str:
        signerAddress = await self._retrieve_signature_signer_address(signatureString=signatureString)
        user = await self._get_user_by_wallet_address(walletAddress=signerAddress)
        return user.userId

    async def _get_user_by_wallet_address(self, walletAddress: str) -> User:
        try:
            user = await self.userManager.get_user_by_wallet_address(walletAddress=walletAddress)
        except NotFoundException:
            raise UnauthorizedException('NO_USER')
        return user

    async def user_login_with_wallet_address(self, walletAddress: str, userId: str) -> User:
        try:
            user = await self.userManager.get_user_by_wallet_address(walletAddress=walletAddress)
        except NotFoundException:
            raise UnauthorizedException('NO_USER')
        if user.userId != userId:
            raise ForbiddenException('INCORRECT_USER')
        return user

    async def get_user(self, userId: str) -> User:
        return await self.userManager.get_user(userId=userId)

    async def get_user_by_username(self, username: str) -> User:
        return await self.userManager.get_user_by_username(username=username)

    async def create_user(self, walletAddress: str, username: str) -> User:
        return await self.userManager.create_user(walletAddress=walletAddress, username=username)

    async def get_user_wallet(self, userId: str) -> UserWallet:
        return await self.userManager.get_user_wallet(userId=userId)
