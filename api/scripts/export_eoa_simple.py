# ruff: noqa: T201

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.requester import Requester

from rangeseeker.external.coinbase_cdp_client import CoinbaseCdpClient


async def main() -> None:
    walletAddress = '0x1E15E0B70C7f09A52c62eE0364b88C145c61118e'

    requester = Requester()
    coinbaseCdpClient = CoinbaseCdpClient(
        requester=requester,
        walletSecret=os.environ['CDP_WALLET_SECRET'],
        apiKeyName=os.environ['CDP_API_KEY_NAME_2'],
        apiKeyPrivateKey=os.environ['CDP_API_KEY_PRIVATE_KEY_2'],
    )

    print(f'Exporting private key for wallet: {walletAddress}')
    print('=' * 60)

    privateKey = await coinbaseCdpClient.export_eoa(walletAddress=walletAddress)

    print(f'\nPrivate Key: {privateKey}')

    print('=' * 60)
    print('\n⚠️  Keep this private key secure!')


if __name__ == '__main__':
    asyncio.run(main())
