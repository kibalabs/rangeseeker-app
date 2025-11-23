# ruff: noqa: T201

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncclick as click
from core import logging

from rangeseeker.create_app_manager import create_app_manager


@click.command()
@click.option('-a', '--agent-id', 'agentId', required=True, type=str, help='Agent ID to rebalance')
async def main(agentId: str) -> None:
    logging.basicConfig(level=logging.INFO)
    appManager = create_app_manager()
    await appManager.database.connect()

    try:
        async with appManager.database.create_context_connection():
            # Get agent details
            agent = await appManager.userManager.get_agent_raw(agentId=agentId)
            agentWallet = await appManager.userManager.get_agent_wallet(userId=agent.userId, agentId=agentId)

            print(f'Agent ID: {agentId}')
            print(f'Wallet: {agentWallet.walletAddress}')
            print(f'\n📊 BEFORE REBALANCE:')
            print('=' * 80)

            # Get current balances
            balances = await appManager.get_wallet_balances(chainId=8453, walletAddress=agentWallet.walletAddress)
            positions = await appManager.get_wallet_uniswap_positions(walletAddress=agentWallet.walletAddress)

            print(f'\nToken Balances:')
            totalValue = 0.0
            for balance in balances:
                amount = float(balance.balance) / (10**balance.asset.decimals)
                valueUsd = amount * balance.assetPrice.priceUsd
                print(f'  {balance.asset.symbol}: {amount:.6f} (${valueUsd:.2f})')
                totalValue += valueUsd

            print(f'\nUniswap V3 Positions:')
            if positions:
                for pos in positions:
                    print(f'  Token ID: {pos.tokenId}')
                    print(f'    Pool: {pos.poolAddress}')
                    print(f'    {pos.token0}: {pos.token0Amount:.6f} (${pos.token0ValueUsd:.2f})')
                    print(f'    {pos.token1}: {pos.token1Amount:.2f} (${pos.token1ValueUsd:.2f})')
                    print(f'    Total: ${pos.totalValueUsd:.2f}')
                    totalValue += pos.totalValueUsd
            else:
                print('  None')

            print(f'\nTotal Value: ${totalValue:.2f}')

            print('\n🔄 TRIGGERING REBALANCE...')
            print('=' * 80)

            await appManager.deposit_made_to_agent(
                userId=agent.userId,
                agentId=agentId,
            )

            print('\n📊 AFTER REBALANCE:')
            print('=' * 80)

            # Get updated balances
            balances = await appManager.get_wallet_balances(chainId=8453, walletAddress=agentWallet.walletAddress)
            positions = await appManager.get_wallet_uniswap_positions(walletAddress=agentWallet.walletAddress)

            print(f'\nToken Balances:')
            totalValue = 0.0
            for balance in balances:
                amount = float(balance.balance) / (10**balance.asset.decimals)
                valueUsd = amount * balance.assetPrice.priceUsd
                print(f'  {balance.asset.symbol}: {amount:.6f} (${valueUsd:.2f})')
                totalValue += valueUsd

            print(f'\nUniswap V3 Positions:')
            if positions:
                for pos in positions:
                    print(f'  Token ID: {pos.tokenId}')
                    print(f'    Pool: {pos.poolAddress}')
                    print(f'    {pos.token0}: {pos.token0Amount:.6f} (${pos.token0ValueUsd:.2f})')
                    print(f'    {pos.token1}: {pos.token1Amount:.2f} (${pos.token1ValueUsd:.2f})')
                    print(f'    Total: ${pos.totalValueUsd:.2f}')
                    totalValue += pos.totalValueUsd
            else:
                print('  None')

            print(f'\nTotal Value: ${totalValue:.2f}')
            print('\n✅ Rebalance completed!')
    finally:
        await appManager.database.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
