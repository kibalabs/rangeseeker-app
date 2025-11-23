# ruff: noqa: T201

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rangeseeker.external.amp_client import AmpClient


def to_str(val: object) -> str:
    """Convert any value to string, handling bytes specially."""
    if isinstance(val, bytes):
        return '0x' + val.hex()
    return str(val) if val is not None else 'None'


async def main() -> None:
    token = os.environ.get('THEGRAPHAMP_API_KEY', '')
    ampClient = AmpClient(flightUrl='https://gateway.amp.staging.thegraph.com', token=token)
    datasetName = 'edgeandnode/uniswap_v3_base@0.0.1'

    # Test wallet address from the logs
    walletAddress = '0x1E15E0B70C7f09A52c62eE0364b88C145c61118e'.lower()
    positionManagerAddress = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1'.lower()

    print(f'Querying positions for wallet: {walletAddress}')
    print(f'Position Manager: {positionManagerAddress}')
    print()

    # Check IncreaseLiquidity events - this is triggered when position is minted!
    print('=== Query 1: IncreaseLiquidity events (position mints) ===')
    sql_increase = f"""
    SELECT
        event."tokenId" as token_id,
        event."liquidity" as liquidity,
        event."amount0" as amount0,
        event."amount1" as amount1,
        block_num,
        timestamp,
        tx_hash
    FROM "{datasetName}".event__position_manager_increase_liquidity
    WHERE
        position_manager_address = X'{positionManagerAddress[2:]}'
    ORDER BY block_num DESC
    LIMIT 20
    """

    print(f'SQL:\n{sql_increase}\n')

    async for row in ampClient.execute_sql(sql_increase):
        print(
            f'IncreaseLiquidity: token_id={to_str(row.get("token_id"))}, liquidity={to_str(row.get("liquidity"))}, amount0={to_str(row.get("amount0"))}, amount1={to_str(row.get("amount1"))}, block={to_str(row.get("block_num"))}, tx={to_str(row.get("tx_hash"))}'
        )

    print()

    # Check Collect events
    print('=== Query 2: Collect events ===')
    sql_collect = f"""
    SELECT
        event."tokenId" as token_id,
        event."amount0" as amount0,
        event."amount1" as amount1,
        event."recipient" as recipient,
        block_num,
        timestamp,
        tx_hash
    FROM "{datasetName}".event__position_manager_collect
    WHERE
        position_manager_address = X'{positionManagerAddress[2:]}'
    ORDER BY block_num DESC
    LIMIT 20
    """

    print(f'SQL:\n{sql_collect}\n')

    async for row in ampClient.execute_sql(sql_collect):
        print(f'Collect: token_id={to_str(row.get("token_id"))}, amount0={to_str(row.get("amount0"))}, amount1={to_str(row.get("amount1"))}, recipient={to_str(row.get("recipient"))}, block={to_str(row.get("block_num"))}')

    print()

    # Check DecreaseLiquidity events
    print('=== Query 3: DecreaseLiquidity events ===')
    sql_decrease = f"""
    SELECT
        event."tokenId" as token_id,
        event."liquidity" as liquidity,
        event."amount0" as amount0,
        event."amount1" as amount1,
        block_num,
        timestamp,
        tx_hash
    FROM "{datasetName}".event__position_manager_decrease_liquidity
    WHERE
        position_manager_address = X'{positionManagerAddress[2:]}'
    ORDER BY block_num DESC
    LIMIT 20
    """

    print(f'SQL:\n{sql_decrease}\n')

    async for row in ampClient.execute_sql(sql_decrease):
        print(
            f'DecreaseLiquidity: token_id={to_str(row.get("token_id"))}, liquidity={to_str(row.get("liquidity"))}, amount0={to_str(row.get("amount0"))}, amount1={to_str(row.get("amount1"))}, block={to_str(row.get("block_num"))}, tx={to_str(row.get("tx_hash"))}'
        )

    print()

    # Now let's try to find our specific transaction
    print('=== Query 4: Finding our transaction from the logs ===')
    # From logs: [UNISWAP] Mint transaction broadcast successfully: 0x8d71e782a3986e18d5346ab3e447a2095d174995179cc1de74b11df9bfa54686
    # Actually that was approval, the mint was after that
    # Let's search for recent IncreaseLiquidity with our wallet in the recipient

    sql_our_positions = f"""
    SELECT
        event."tokenId" as token_id,
        event."liquidity" as liquidity,
        event."amount0" as amount0,
        event."amount1" as amount1,
        block_num,
        timestamp,
        tx_hash,
        log_index
    FROM "{datasetName}".event__position_manager_increase_liquidity
    WHERE
        position_manager_address = X'{positionManagerAddress[2:]}'
        AND block_num >= 38538200
    ORDER BY block_num DESC
    LIMIT 50
    """

    print(f'SQL:\n{sql_our_positions}\n')

    positions = []
    async for row in ampClient.execute_sql(sql_our_positions):
        print(f'Position: token_id={to_str(row.get("token_id"))}, liquidity={to_str(row.get("liquidity"))}, amount0={to_str(row.get("amount0"))}, amount1={to_str(row.get("amount1"))}, block={to_str(row.get("block_num"))}, tx={to_str(row.get("tx_hash"))}')
        positions.append(row)

    print(f'\nTotal positions found: {len(positions)}')


if __name__ == '__main__':
    asyncio.run(main())
