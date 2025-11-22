import base64
import hashlib
import json
import secrets
import time
import typing
import uuid
from urllib.parse import urlparse

import jwt
from core.exceptions import KibaException
from core.http.rest_method import RestMethod
from core.requester import Requester
from core.util import chain_util
from core.util.typing_util import Json
from core.util.typing_util import JsonObject
from cryptography.hazmat.primitives import asymmetric
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from pydantic import BaseModel

from rangeseeker import constants

BASE_CHAIN_ID = 8453


class ClientAssetBalance(BaseModel):
    assetAddress: str
    balance: int
    name: str
    symbol: str
    decimals: int


def sort_json_object(obj: typing.Any) -> typing.Any:  # type: ignore[explicit-any]
    if not obj or not isinstance(obj, dict | list):
        return obj
    if isinstance(obj, list):
        return [sort_json_object(item) for item in obj]
    return {key: sort_json_object(obj[key]) for key in sorted(obj.keys())}


# Lots copied from https://github.com/coinbase/cdp-sdk-python/blob/master/cdp/cdp_api_client.py
class CoinbaseCdpClient:
    def __init__(
        self,
        requester: Requester,
        walletSecret: str,
        apiKeyName: str,
        apiKeyPrivateKey: str,
    ) -> None:
        self.requester = requester
        self.walletSecret = walletSecret
        self.apiKeyName = apiKeyName
        self.apiKeyPrivateKey = apiKeyPrivateKey

    def _parse_private_key(self, keyString: str) -> PrivateKeyTypes:
        keyData = keyString.encode()
        try:
            return serialization.load_pem_private_key(keyData, password=None)
        except Exception as exception:
            decodedKey = base64.b64decode(keyString)
            if len(decodedKey) == 32:  # noqa: PLR2004
                return asymmetric.ed25519.Ed25519PrivateKey.from_private_bytes(decodedKey)
            if len(decodedKey) == 64:  # noqa: PLR2004
                return asymmetric.ed25519.Ed25519PrivateKey.from_private_bytes(decodedKey[:32])
            raise KibaException('Ed25519 private key must be 32 or 64 bytes after base64 decoding') from exception

    def _signable_uri(self, url: str, method: str) -> str:
        parsedUrl = urlparse(url)
        return f'{method} {parsedUrl.netloc}{parsedUrl.path}'

    def _build_api_jwt(self, url: str, method: str) -> str:
        now = int(time.time())
        privateKey = self._parse_private_key(keyString=self.apiKeyPrivateKey)
        if isinstance(privateKey, asymmetric.ec.EllipticCurvePrivateKey):
            alg = 'ES256'
        elif isinstance(privateKey, asymmetric.ed25519.Ed25519PrivateKey):
            alg = 'EdDSA'
        else:
            raise KibaException('Unsupported key type')
        header = {
            'alg': alg,
            'kid': self.apiKeyName,
            'typ': 'JWT',
            'nonce': secrets.token_hex(),
        }
        claims = {
            'sub': self.apiKeyName,
            'iss': 'cdp',
            'aud': ['cdp_service'],
            'nbf': now,
            'exp': now + 60,
            'uris': [self._signable_uri(url=url, method=method)],
        }
        return jwt.encode(claims, privateKey, algorithm=alg, headers=header)

    def _build_wallet_jwt(self, url: str, method: str, body: Json | None) -> str:
        now = int(time.time())
        uri = self._signable_uri(url=url, method=method)
        payload = {'iat': now, 'nbf': now, 'jti': str(uuid.uuid4()), 'uris': [uri]}
        if body:
            if not isinstance(body, dict):
                raise KibaException('Body must be a dictionary')
            sortedBody = sort_json_object(body)
            bodyString = json.dumps(sortedBody, separators=(',', ':'), sort_keys=True)
            bodyHash = hashlib.sha256(bodyString.encode('utf-8')).hexdigest()
            payload['reqHash'] = bodyHash
        derKeyBytes = serialization.load_der_private_key(data=base64.b64decode(self.walletSecret), password=None)
        token = jwt.encode(
            payload=payload,
            key=typing.cast(asymmetric.ec.EllipticCurvePrivateKey, derKeyBytes),
            algorithm='ES256',
            headers={'typ': 'JWT'},
        )
        return token

    def _build_api_headers(self, url: str, method: str) -> dict[str, str]:
        apiAuthToken = self._build_api_jwt(url=url, method=method)
        headers = {
            'Authorization': f'Bearer {apiAuthToken}',
            'Content-Type': 'application/json',
        }
        return headers

    def _build_wallet_api_headers(self, url: str, method: str, body: Json | None = None) -> dict[str, str]:
        walletAuthToken = self._build_wallet_jwt(url=url, method=method, body=body)
        apiHeaders = self._build_api_headers(url=url, method=method)
        headers = {
            **apiHeaders,
            'X-Wallet-Auth': walletAuthToken,
        }
        return headers

    async def create_eoa(self, name: str) -> str:
        method = RestMethod.POST
        url = 'https://api.cdp.coinbase.com/platform/v2/evm/accounts'
        payload = {
            'name': name,
            # "accountPolicy": ""
        }
        headers = self._build_wallet_api_headers(url=url, method=method, body=payload)
        response = await self.requester.make_request(method=method, url=url, dataDict=payload, headers=headers)
        responseDict = response.json()
        address: str = str(responseDict['address'])
        return address

    async def get_eoa_by_name(self, name: str) -> str:
        method = RestMethod.GET
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/accounts/by-name/{name}'
        headers = self._build_api_headers(url=url, method=method)
        response = await self.requester.make_request(method=method, url=url, headers=headers)
        responseDict = response.json()
        address: str = str(responseDict['address'])
        return address

    async def get_wallet_asset_balances(self, chainId: int, walletAddress: str) -> list[ClientAssetBalance]:
        if chainId == constants.BASE_CHAIN_ID:
            network = 'base'
        else:
            raise KibaException(f'Unsupported chainId: {chainId}')
        allBalances: list[ClientAssetBalance] = []
        pageToken: str | None = None
        method = RestMethod.GET
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/token-balances/{network}/{walletAddress}'
        dataDict: JsonObject = {'pageSize': 50}
        while True:
            if pageToken:
                dataDict['pageToken'] = pageToken
            headers = self._build_api_headers(url=url, method=method)
            response = await self.requester.make_request(method=method, url=url, headers=headers, dataDict=dataDict)
            responseDict = response.json()
            allBalances.extend(
                [
                    ClientAssetBalance(
                        assetAddress=chain_util.normalize_address(balance['token']['contractAddress']),
                        balance=int(balance['amount']['amount']),
                        name=balance['token'].get('name', ''),
                        symbol=balance['token'].get('symbol', ''),
                        decimals=int(balance['amount']['decimals']),
                    )
                    for balance in responseDict['balances']
                ]
            )
            pageToken = responseDict.get('nextPageToken')
            if not pageToken:
                break
        return allBalances
