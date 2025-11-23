import typing
from typing import Any
from typing import NotRequired
from typing import TypedDict

from core.requester import Requester
from core.web3.eth_client import RestEthClient
from web3.types import TxParams


class Permit2(TypedDict):
    type: str
    hash: str
    eip712: NotRequired[dict[str, Any] | None]  # type: ignore[explicit-any]


class ZeroExFee(TypedDict):
    amount: str
    token: str
    type: str


class Fees(TypedDict):
    integratorFee: NotRequired[Any | None]  # type: ignore[explicit-any]
    zeroExFee: ZeroExFee
    gasFee: NotRequired[Any | None]  # type: ignore[explicit-any]


class Issues(TypedDict):
    allowance: dict[str, Any]  # type: ignore[explicit-any]
    balance: dict[str, Any]  # type: ignore[explicit-any]
    simulationIncomplete: bool
    invalidSourcesPassed: list[Any]  # type: ignore[explicit-any]


class ZeroxPermit2QuoteResponse(TypedDict):
    blockNumber: str
    buyAmount: str
    buyToken: str
    fees: Fees
    issues: Issues
    liquidityAvailable: bool
    minBuyAmount: str
    # NOTE(krishan711): route not included
    permit2: Permit2
    sellAmount: str
    sellToken: str
    totalNetworkFee: str
    transaction: TxParams


class ZeroxQuoteResponse(TypedDict):
    blockNumber: str
    buyAmount: str
    buyToken: str
    fees: Fees
    issues: Issues
    liquidityAvailable: bool
    minBuyAmount: str
    # NOTE(krishan711): route not included
    sellAmount: str
    sellToken: str
    totalNetworkFee: str
    transaction: TxParams


class ZeroxClient:
    def __init__(self, requester: Requester, apiKey: str, ethClient: RestEthClient) -> None:
        self.requester = requester
        self.apiKey = apiKey
        self.ethClient = ethClient

    def get_address_for_chain(self, chainId: int) -> str:  # noqa: ARG002
        # https://0x.org/docs/developer-resources/core-concepts/contracts
        return '0x0000000000001fF3684f28c67538d4D072C22734'

    def get_permit2_address_for_chain(self, chainId: int) -> str:  # noqa: ARG002
        # https://0x.org/docs/developer-resources/core-concepts/contracts
        return '0x000000000022D473030F116dDEE9F6B43aC78BA3'

    async def get_price(self, chainId: int, amount: int, fromAssetAddress: str, toAssetAddress: str) -> int:
        response = await self.requester.get(
            url='https://api.0x.org/swap/permit2/price',
            dataDict={
                'chainId': chainId,
                'sellToken': fromAssetAddress,
                'sellAmount': amount,
                'buyToken': toAssetAddress,
            },
            headers={
                '0x-api-key': self.apiKey,
                '0x-version': 'v2',
            },
        )
        responseDict = response.json()
        return int(responseDict['minBuyAmount'])

    async def prepare_permit2_quote(
        self,
        chainId: int,
        amount: int,
        fromAssetAddress: str,
        toAssetAddress: str,
        fromWalletAddress: str,
    ) -> ZeroxPermit2QuoteResponse:
        response = await self.requester.get(
            url='https://api.0x.org/swap/permit2/quote',
            dataDict={
                'chainId': chainId,
                'sellToken': fromAssetAddress,
                'sellAmount': amount,
                'buyToken': toAssetAddress,
                'taker': fromWalletAddress,
                'tradeSurplusRecipient': '0xF3A535cEdf65cB8C287Cb5CAc67E970E94eb372D',  # tokenpage.eth
            },
            headers={
                '0x-api-key': self.apiKey,
                '0x-version': 'v2',
            },
        )
        responseDict = response.json()
        return typing.cast(ZeroxPermit2QuoteResponse, responseDict)

    async def prepare_quote(
        self,
        chainId: int,
        amount: int,
        fromAssetAddress: str,
        toAssetAddress: str,
        fromWalletAddress: str,
    ) -> ZeroxQuoteResponse:
        response = await self.requester.get(
            url='https://api.0x.org/swap/allowance-holder/quote',
            dataDict={
                'chainId': chainId,
                'sellToken': fromAssetAddress,
                'sellAmount': amount,
                'buyToken': toAssetAddress,
                'taker': fromWalletAddress,
                'tradeSurplusRecipient': '0xF3A535cEdf65cB8C287Cb5CAc67E970E94eb372D',  # tokenpage.eth
            },
            headers={
                '0x-api-key': self.apiKey,
                '0x-version': 'v2',
            },
        )
        responseDict = response.json()
        return typing.cast(ZeroxQuoteResponse, responseDict)
