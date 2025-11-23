# ruff: noqa: T201

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rangeseeker.external.amp_client import AmpClient
from rangeseeker.external.uniswap_data_client import UniswapDataClient


async def main() -> None:
    token = os.environ.get('THEGRAPHAMP_API_KEY', '')
    ampClient = AmpClient(flightUrl='https://gateway.amp.staging.thegraph.com', token=token)
    uniswapClient = UniswapDataClient(ampClient=ampClient)

    # My agent wallet from the rebalance
    walletAddress = '0x1E15E0B70C7f09A52c62eE0364b88C145c61118e'

    print(f'Querying positions for wallet: {walletAddress}\n')

    positions = await uniswapClient.get_wallet_positions(walletAddress)

    print(f'Found {len(positions)} position(s)\n')

    for position in positions:
        print(f'Position #{position.tokenId}')
        print(f'  Amount0: {position.amount0}')
        print(f'  Amount1: {position.amount1}')
        print()


if __name__ == '__main__':
    asyncio.run(main())
