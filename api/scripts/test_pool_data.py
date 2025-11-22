# ruff: noqa: T201
import asyncio
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rangeseeker.external.amp_client import AmpClient
from rangeseeker.external.uniswap_data_client import UniswapDataClient

CHAIN_ID = 8453
WETH_ADDRESS = '0x4200000000000000000000000000000000000006'
USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

AMP_TOKEN = os.environ['THEGRAPHAMP_API_KEY']


async def main() -> None:
    print('=' * 80)
    print('POOL DATA TEST')
    print('=' * 80)
    print()
    print(f'Chain ID: {CHAIN_ID}')
    print(f'Token 0 (WETH): {WETH_ADDRESS}')
    print(f'Token 1 (USDC): {USDC_ADDRESS}')
    print()

    ampClient = AmpClient(
        flightUrl='https://gateway.amp.staging.thegraph.com',
        token=AMP_TOKEN,
    )
    uniswapClient = UniswapDataClient(ampClient=ampClient)

    print('Fetching pool...')
    pool = await uniswapClient.get_pool(token0Address=WETH_ADDRESS, token1Address=USDC_ADDRESS)
    print(f'✓ Pool Address: {pool.address}')
    print(f'  Fee Tier: {pool.fee / 10000}%')
    print(f'  Liquidity: {pool.liquidity:,}')
    print()

    print('Fetching current price...')
    currentPrice = await uniswapClient.get_current_price(poolAddress=pool.address)
    print(f'✓ Current Price: ${currentPrice:,.2f}')
    print()

    print('Fetching 24h volatility...')
    volatility24h = await uniswapClient.get_pool_volatility(poolAddress=pool.address, hoursBack=24)
    print(f'✓ 24h Volatility:')
    print(f'  Realized: {volatility24h.realized * 100:.2f}%')
    print(f'  Annualized: {volatility24h.annualized * 100:.2f}%')
    print()

    print('Fetching 7d volatility...')
    volatility7d = await uniswapClient.get_pool_volatility(poolAddress=pool.address, hoursBack=168)
    print(f'✓ 7d Volatility:')
    print(f'  Realized: {volatility7d.realized * 100:.2f}%')
    print(f'  Annualized: {volatility7d.annualized * 100:.2f}%')
    print()

    print('Fetching pool fee data...')
    feeGrowth7d = await uniswapClient.get_pool_fee_growth(poolAddress=pool.address, hoursBack=168)
    feeRate = pool.fee / 1_000_000.0
    print(f'✓ Pool Fee Data:')
    print(f'  7d Fee Growth (USD per unit liquidity): {feeGrowth7d}')
    print(f'  Fee Rate: {feeRate * 100:.4f}%')
    print()

    print('Testing earnings estimates for different strategy ranges...')
    print()

    for rangePercent in [0.02, 0.04, 0.08]:
        print(f'Range: ±{rangePercent * 100:.0f}%')
        price = currentPrice
        priceA = price * (1 - rangePercent)
        priceB = price * (1 + rangePercent)
        sqrtP = math.sqrt(price)
        sqrtPa = math.sqrt(priceA)
        sqrtPb = math.sqrt(priceB)
        denominator = (2 * sqrtP) - (price / sqrtPb) - sqrtPa
        liquidityFor100 = 100.0 / denominator if denominator > 0 else 0.0

        dec0 = 18
        dec1 = 6
        liquidityAdjustment = 10 ** ((dec0 + dec1) / 2)
        liquidityFor100Raw = liquidityFor100 * liquidityAdjustment

        weeklyEarningsUsd = feeGrowth7d * feeRate * liquidityFor100Raw
        weeklyPercent = (weeklyEarningsUsd / 100.0) * 100.0
        apyPercent = weeklyPercent * 52

        print(f'  Liquidity (adjusted): {liquidityFor100:,.2f}')
        print(f'  Liquidity (raw): {liquidityFor100Raw:,.2f}')
        print(f'  Weekly Earnings: ${weeklyEarningsUsd:.4f} ({weeklyPercent:.2f}%)')
        print(f'  Estimated APY: {apyPercent:.1f}%')
        print()

    print('=' * 80)
    print('✓ ALL TESTS PASSED')
    print('=' * 80)


if __name__ == '__main__':
    asyncio.run(main())
