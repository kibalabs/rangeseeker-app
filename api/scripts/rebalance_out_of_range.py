# ruff: noqa: T201, SLF001, PLR2004

import asyncio
import datetime
import sys
import typing

from core import logging
from core.util import chain_util
from web3.types import HexStr
from web3.types import TxParams
from web3.types import Wei

from rangeseeker import constants
from rangeseeker.app_manager import AppManager
from rangeseeker.create_app_manager import create_app_manager

logging.basicConfig(level=logging.INFO)


async def deposit_to_uniswap_v3_custom_range(
    appManager: AppManager,
    chainId: int,
    walletAddress: str,
    wethAmount: int,
    usdcAmount: int,
    tickLower: int,
    tickUpper: int,
) -> None:
    """Deposit to Uniswap V3 with custom tick range."""
    logging.info(f'[UNISWAP] Creating position with custom range - lower: {tickLower}, upper: {tickUpper}')

    positionManagerAddress = constants.CHAIN_UNISWAP_V3_NONFUNGIBLE_POSITION_MANAGER_MAP[chainId]
    token0 = constants.CHAIN_WETH_MAP[chainId]
    token1 = constants.CHAIN_USDC_MAP[chainId]
    fee = 500  # 0.05% fee tier
    amount0Min = 0
    amount1Min = 0
    deadline = int(datetime.datetime.now(tz=datetime.UTC).timestamp()) + 1200

    logging.info(f'[UNISWAP] Token amounts - WETH: {wethAmount}, USDC: {usdcAmount}')
    logging.info(f'[UNISWAP] Checking/approving WETH to position manager')
    await appManager._approve_token_if_needed(chainId, walletAddress, token0, positionManagerAddress, wethAmount)
    logging.info(f'[UNISWAP] Checking/approving USDC to position manager')
    await appManager._approve_token_if_needed(chainId, walletAddress, token1, positionManagerAddress, usdcAmount)

    data = appManager._encode_mint_params(
        token0=token0,
        token1=token1,
        fee=fee,
        tickLower=tickLower,
        tickUpper=tickUpper,
        amount0Desired=wethAmount,
        amount1Desired=usdcAmount,
        amount0Min=amount0Min,
        amount1Min=amount1Min,
        recipient=walletAddress,
        deadline=deadline,
    )

    logging.info('[UNISWAP] Broadcasting mint transaction')
    transactionDict: TxParams = {
        'from': chain_util.normalize_address(value=walletAddress),
        'to': chain_util.normalize_address(value=positionManagerAddress),
        'value': Wei(0),
        'data': typing.cast(HexStr, data),
    }
    filledTransaction = await appManager.ethClient.fill_transaction_params(
        params=transactionDict,
        fromAddress=walletAddress,
        chainId=chainId,
    )
    signedTx = await appManager.userManager.coinbaseCdpClient.sign_transaction(
        walletAddress=walletAddress,
        transactionDict=filledTransaction,
    )
    txHash = await appManager.ethClient.send_raw_transaction(transactionData=signedTx)
    logging.info(f'[UNISWAP] Mint transaction broadcast: {txHash}')
    receipt = await appManager.ethClient.wait_for_transaction_receipt(transactionHash=txHash)
    logging.info(f'[UNISWAP] Mint transaction mined in block {receipt["blockNumber"]}')


async def rebalance_out_of_range(agent_id: str, offset_percent: float = 20.0) -> None:
    """
    Rebalance an agent's position but place it outside the current range.

    Args:
        agent_id: The agent ID to rebalance
        offset_percent: How far above the current price to place the range (default 20%)
    """
    appManager = create_app_manager()
    await appManager.database.connect()

    try:
        async with appManager.database.create_context_connection():
            # Get agent
            agent = await appManager.userManager.get_agent_raw(agentId=agent_id)
            user_id = agent.userId

            agentWallet = await appManager.userManager.get_agent_wallet(userId=user_id, agentId=agent_id)
            logging.info(f'Agent wallet address: {agentWallet.walletAddress}')

            # Withdraw existing positions
            positions = await appManager.get_wallet_uniswap_positions(walletAddress=agentWallet.walletAddress)
            if positions:
                logging.info(f'Found {len(positions)} existing positions, withdrawing...')
                for position in positions:
                    logging.info(f'Withdrawing position {position.tokenId}')
                    await appManager._withdraw_from_uniswap_v3(
                        chainId=constants.BASE_CHAIN_ID,
                        walletAddress=agentWallet.walletAddress,
                        tokenId=position.tokenId,
                    )
                logging.info('All positions withdrawn')

            # Get current balances
            balances = await appManager.get_wallet_balances(chainId=constants.BASE_CHAIN_ID, walletAddress=agentWallet.walletAddress)
            wethBalance = next((b for b in balances if b.asset.address == constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID]), None)
            usdcBalance = next((b for b in balances if b.asset.address == constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID]), None)

            if not wethBalance or not usdcBalance:
                raise ValueError('Agent wallet must have WETH and USDC balances')

            logging.info(f'Current balances - WETH: {wethBalance.balance}, USDC: {usdcBalance.balance}')

            # Get current pool state
            pool = await appManager.strategyManager.uniswapClient.get_pool(
                token0Address=constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID],
                token1Address=constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID],
                feeTier=500,
            )
            currentTick = pool.tick
            logging.info(f'Current pool tick: {currentTick}')

            # Calculate tick range ABOVE current price for demo
            tickSpacing = 10
            rangePercent = 0.1  # 10% range width

            # Offset the range above the current price
            # 1% price change ≈ 100 ticks, so offset_percent% ≈ offset_percent * 100 ticks
            tickOffset = int((offset_percent / 100) * 10000)
            tickOffset = (tickOffset // tickSpacing) * tickSpacing  # Round to tick spacing

            tickRange = int((rangePercent * 10000) / tickSpacing) * tickSpacing

            # Place range ABOVE current price
            tickLower = ((currentTick + tickOffset) // tickSpacing) * tickSpacing
            tickUpper = ((currentTick + tickOffset + tickRange) // tickSpacing) * tickSpacing

            logging.info(f'Placing position OUT OF RANGE:')
            logging.info(f'  Current tick: {currentTick}')
            logging.info(f'  Offset: {tickOffset} ticks ({offset_percent}%)')
            logging.info(f'  New range: {tickLower} to {tickUpper}')
            logging.info(f'  This is {((tickLower - currentTick) / 100):.1f}% above current price')

            # Create the out-of-range position
            await deposit_to_uniswap_v3_custom_range(
                appManager=appManager,
                chainId=constants.BASE_CHAIN_ID,
                walletAddress=agentWallet.walletAddress,
                wethAmount=wethBalance.balance,
                usdcAmount=usdcBalance.balance,
                tickLower=tickLower,
                tickUpper=tickUpper,
            )

            logging.info('✅ Successfully created out-of-range position for demo!')
    finally:
        await appManager.database.disconnect()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python rebalance_out_of_range.py <agent_id> [offset_percent]')
        print('  agent_id: The agent ID to rebalance')
        print('  offset_percent: How far above current price to place range (default: 20%)')
        sys.exit(1)

    agent_id = sys.argv[1]
    offset_percent = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

    asyncio.run(rebalance_out_of_range(agent_id, offset_percent))
