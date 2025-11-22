# ruff: noqa: T201

import asyncio
import json
import os

from rangeseeker.amp_client import AmpClient

# Configuration
AMP_TOKEN = os.environ['THEGRAPHAMP_API_KEY']

# Edit this query to test different SQL statements
QUERY = """
SELECT
    block_num,
    timestamp,
    tx_hash,
    log_index,
    data,
    topic1,
    topic2,
    topic3
FROM "edgeandnode/base_mainnet@0.0.1".logs
WHERE
    address = 0xd0b53D9277642d899DF5C87A3966A349A798F224
    -- AND topic0 = decode('c42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67', 'hex')
    AND block_num >= 38400369
-- ORDER BY timestamp DESC
LIMIT 1000
"""


async def main() -> None:
    """Execute test query against AMP."""
    print('=' * 80)
    print('THEGRAPH AMP CLIENT TEST')
    print('=' * 80)
    print()

    # Initialize AMP client
    client = AmpClient(
        flightUrl='https://gateway.amp.staging.thegraph.com',
        token=AMP_TOKEN,
    )

    print('Query:')
    print('-' * 80)
    print(QUERY.strip())
    print('-' * 80)
    print()

    print('Executing query...')
    print()
    print('Results:')
    print('-' * 80)

    rowCount = 0
    async for row in client.execute_sql(QUERY):
        rowCount += 1
        print(f'\nRow {rowCount}:')
        print(json.dumps(row, indent=2, default=str))

    print()
    print('-' * 80)
    print(f'✓ Query complete - {rowCount} rows returned')

    print()
    print('=' * 80)


if __name__ == '__main__':
    asyncio.run(main())
