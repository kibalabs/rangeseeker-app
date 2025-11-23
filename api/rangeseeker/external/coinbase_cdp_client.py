import base64
import hashlib
import json
import secrets
import time
import typing
import uuid
from urllib.parse import urlparse

import jwt
import rlp  # type: ignore[import-untyped]
from core import logging
from core.exceptions import KibaException
from core.http.rest_method import RestMethod
from core.requester import Requester
from core.util import chain_util
from core.util.typing_util import Json
from core.util.typing_util import JsonObject
from cryptography.hazmat.primitives import asymmetric
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from eth_utils import encode_hex
from eth_utils import to_bytes
from pydantic import BaseModel
from web3.types import TxParams

from rangeseeker import constants

BASE_CHAIN_ID = 8453

IMPORT_ACCOUNT_PUBLIC_RSA_KEY = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA2Fxydgm/ryYk0IexQIuL
9DKyiIk2WmS36AZ83a9Z0QX53qdveg08b05g1Qr+o+COoYOT/FDi8anRGAs7rIyS
uigrjHR6VrmFjnGrrTr3MINwC9cYQFHwET8YVGRq+BB3iFTB1kIb9XJ/vT2sk1xP
hJ6JihEwSl4DgbeVjqw59wYqrNg355oa8EdFqkmfGU2tpbM56F8iv1F+shwkGo3y
GhW/UOQ5OLauXvsqo8ranwsK+lqFblLEMlNtn1VSJeO2vMxryeKFrY2ob8VqGchC
ftPJiLWs2Du6juw4C1rOWwSMlXzZ6cNMHkxdTcEHMr3C2TEHgzjZY41whMwNTB8q
/pxXnIbH77caaviRs4R/POe8cSsznalXj85LULvFWOIHp0w+jEYSii9Rp9XtHWAH
nrK/O/SVDtT1ohp2F+Zg1mojTgKfLOyGdOUXTi95naDTuG770rSjHdL80tJBz1Fd
+1pzGTGXGHLZQLX5YZm5iuy2cebWfF09VjIoCIlDB2++tr4M+O0Z1X1ZE0J5Ackq
rOluAFalaKynyH3KMyRg+NuLmibu5OmcMjCLK3D4X1YLiN2OK8/bbpEL8JYroDwb
EXIUW5mGS06YxfSUsxHzL9Tj00+GMm/Gvl0+4/+Vn8IXVHjQOSPNEy3EnqCiH/OW
8v0IMC32CeGrX7mGbU+MzlsCAwEAAQ==
-----END PUBLIC KEY-----"""


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

    async def export_eoa(self, walletAddress: str) -> str:
        rsaPrivateKey = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsaPublicKey = rsaPrivateKey.public_key()
        publicKeyDer = rsaPublicKey.public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        exportEncryptionKey = base64.b64encode(publicKeyDer).decode('utf-8')
        method = RestMethod.POST
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/accounts/{walletAddress}/export'
        dataDict = {
            'exportEncryptionKey': exportEncryptionKey,
        }
        headers = self._build_wallet_api_headers(url=url, method=method, body=dataDict)
        response = await self.requester.make_request(method=method, url=url, dataDict=dataDict, headers=headers)
        responseDict = response.json()
        encryptedPrivateKeyBytes = base64.b64decode(responseDict['encryptedPrivateKey'])
        decryptedPrivateKeyBytes = rsaPrivateKey.decrypt(
            ciphertext=encryptedPrivateKeyBytes,
            padding=asymmetric.padding.OAEP(
                mgf=asymmetric.padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        privateKeyHex = '0x' + decryptedPrivateKeyBytes.hex()
        logging.info(f'private key: {privateKeyHex}')
        return privateKeyHex

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

    async def sign_transaction(self, walletAddress: str, transactionDict: TxParams) -> str:
        method = RestMethod.POST
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/accounts/{walletAddress}/sign/transaction'
        transactionParts = [
            int(transactionDict['chainId'], 16) if isinstance(transactionDict['chainId'], str) else int(transactionDict['chainId']),  # type: ignore[unreachable]
            int(transactionDict['nonce'], 16) if isinstance(transactionDict['nonce'], str) else int(transactionDict['nonce']),  # type: ignore[unreachable]
            int(transactionDict['maxPriorityFeePerGas'], 16) if isinstance(transactionDict['maxPriorityFeePerGas'], str) else int(transactionDict['maxPriorityFeePerGas']),
            int(transactionDict['maxFeePerGas'], 16) if isinstance(transactionDict['maxFeePerGas'], str) else int(transactionDict['maxFeePerGas']),
            int(transactionDict['gas'], 16) if isinstance(transactionDict['gas'], str) else int(transactionDict['gas']),  # type: ignore[unreachable]
            to_bytes(hexstr=transactionDict['to']),
            int(transactionDict['value'], 16) if isinstance(transactionDict['value'], str) else int(transactionDict['value']),  # type: ignore[unreachable]
            to_bytes(hexstr=transactionDict['data']),
            transactionDict.get('accessList', []),
        ]
        transactionStringBytes = b'\x02' + rlp.encode(transactionParts)
        transactionString = encode_hex(transactionStringBytes)
        dataDict = {'transaction': transactionString}
        headers = self._build_wallet_api_headers(url=url, method=method, body=dataDict)
        response = await self.requester.make_request(method=method, url=url, dataDict=dataDict, headers=headers)
        responseDict = response.json()
        return typing.cast(str, responseDict['signedTransaction'])

    async def sign_eip712(self, walletAddress: str, typedData: JsonObject) -> str:
        """Sign EIP-712 typed data using CDP wallet API."""
        method = RestMethod.POST
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/accounts/{walletAddress}/sign/eip712'
        dataDict = {'typedData': typedData}
        headers = self._build_wallet_api_headers(url=url, method=method, body=dataDict)
        response = await self.requester.make_request(method=method, url=url, dataDict=dataDict, headers=headers)
        responseDict = response.json()
        return typing.cast(str, responseDict['signature'])

    async def get_swap_quote(self, chainId: int, walletAddress: str, fromAssetAddress: str, toAssetAddress: str, amount: int) -> JsonObject:
        """Get swap quote from Coinbase CDP API."""
        if chainId == constants.BASE_CHAIN_ID:
            network = 'base'
        else:
            raise KibaException(f'Unsupported chainId: {chainId}')
        method = RestMethod.GET
        url = 'https://api.cdp.coinbase.com/platform/v2/evm/swaps/quote'
        dataDict: JsonObject = {
            'network': network,
            'fromToken': fromAssetAddress,
            'toToken': toAssetAddress,
            'fromAmount': str(amount),
            'taker': walletAddress,
        }
        headers = self._build_api_headers(url=url, method=method)
        response = await self.requester.make_request(method=method, url=url, headers=headers, dataDict=dataDict)
        return typing.cast(JsonObject, response.json())

    async def create_swap(self, chainId: int, walletAddress: str, fromAssetAddress: str, toAssetAddress: str, amount: int) -> JsonObject:
        """Create AND BROADCAST swap transaction via Coinbase CDP API.

        CDP's swap API uses Permit2 which requires:
        1. Getting the swap quote with Permit2 EIP-712 data
        2. Signing the Permit2 message
        3. Broadcasting the transaction with the signed permit

        This method handles all three steps automatically.
        """
        if chainId == constants.BASE_CHAIN_ID:
            network = 'base'
        else:
            raise KibaException(f'Unsupported chainId: {chainId}')

        # Step 1: Get swap quote with Permit2 data
        method = RestMethod.POST
        url = 'https://api.cdp.coinbase.com/platform/v2/evm/swaps'
        payload: JsonObject = {
            'network': network,
            'fromToken': fromAssetAddress,
            'toToken': toAssetAddress,
            'fromAmount': str(amount),
            'taker': walletAddress,
        }
        headers = self._build_wallet_api_headers(url=url, method=method, body=payload)
        response = await self.requester.make_request(method=method, url=url, dataDict=payload, headers=headers)
        swapResponse = typing.cast(JsonObject, response.json())

        # Step 2: Check if this requires Permit2 signing
        permit2Data = swapResponse.get('permit2')
        if permit2Data and isinstance(permit2Data, dict):
            eip712Data = permit2Data.get('eip712')
            if eip712Data and isinstance(eip712Data, dict):
                # Sign the Permit2 EIP-712 message
                permitSignature = await self.sign_eip712(
                    walletAddress=walletAddress,
                    typedData=typing.cast(JsonObject, eip712Data),
                )
                # Store the signature in the response for later use
                permit2DataDict = typing.cast(dict[str, str | JsonObject], permit2Data)
                permit2DataDict['signature'] = permitSignature

        return swapResponse
