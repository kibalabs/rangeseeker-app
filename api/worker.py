import asyncio
import datetime
import os
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]
from core import logging

from rangeseeker.create_app_manager import create_app_manager
from rangeseeker import constants

name = os.environ.get('NAME', 'rangeseeker-worker')
version = os.environ.get('VERSION', 'local')
environment = os.environ.get('ENV', 'dev')
isRunningDebugMode = environment == 'dev'

if isRunningDebugMode:
    logging.init_basic_logging()
else:
    logging.init_json_logging(name=name, version=version, environment=environment)
logging.init_external_loggers(loggerNames=['apscheduler'], loggingLevel=logging.WARNING)


async def check_and_rebalance_agents() -> None:
    """Check all agents and rebalance if needed based on their strategy."""
    startTime = time.time()
    logging.info('[REBALANCE_WORKER] Starting agent rebalance check')

    appManager = create_app_manager()
    await appManager.database.connect()

    try:
        # Get all agents
        agents = await appManager.userManager.database.execute(
            query='SELECT agent_id, user_id, strategy_id FROM agents'
        )

        logging.info(f'[REBALANCE_WORKER] Found {len(list(agents))} agents to check')

        agents = await appManager.userManager.database.execute(
            query='SELECT agent_id, user_id, strategy_id FROM agents'
        )

        for agent_row in agents:
            agent_id = agent_row['agent_id']
            user_id = agent_row['user_id']
            strategy_id = agent_row['strategy_id']

            try:
                logging.info(f'[REBALANCE_WORKER] Checking agent {agent_id}')

                # Get strategy
                strategy = await appManager.strategyManager.get_strategy(strategyId=strategy_id)

                # Get agent wallet
                agentWallet = await appManager.userManager.get_agent_wallet(
                    userId=user_id,
                    agentId=agent_id
                )

                # Get current positions
                positions = await appManager.get_wallet_uniswap_positions(
                    walletAddress=agentWallet.walletAddress
                )

                if not positions:
                    logging.info(f'[REBALANCE_WORKER] Agent {agent_id} has no positions, skipping')
                    continue

                # Get pool state
                pool = await appManager.strategyManager.uniswapClient.get_pool(
                    token0Address=constants.CHAIN_WETH_MAP[constants.BASE_CHAIN_ID],
                    token1Address=constants.CHAIN_USDC_MAP[constants.BASE_CHAIN_ID],
                    feeTier=500,
                )
                currentTick = pool.tick
                currentPrice = appManager.strategyManager.uniswapClient.calculate_price_from_sqrt_price_x96(
                    pool.sqrtPriceX96
                )

                logging.info(f'[REBALANCE_WORKER] Current pool state - tick: {currentTick}, price: {currentPrice:.2f}')

                # Check each position to see if it's out of range
                needsRebalance = False
                for position in positions:
                    if position.tickLower is None or position.tickUpper is None:
                        logging.warning(f'[REBALANCE_WORKER] Position {position.tokenId} missing tick data')
                        continue

                    # Check if current tick is outside the position range
                    if currentTick < position.tickLower or currentTick > position.tickUpper:
                        logging.info(
                            f'[REBALANCE_WORKER] Position {position.tokenId} is OUT OF RANGE - '
                            f'current tick {currentTick} not in [{position.tickLower}, {position.tickUpper}]'
                        )
                        needsRebalance = True
                        break

                    # Calculate how close we are to the edge (as a percentage of the range)
                    rangeSize = position.tickUpper - position.tickLower
                    distanceFromLower = currentTick - position.tickLower
                    distanceFromUpper = position.tickUpper - currentTick

                    # If we're within 10% of either edge, consider rebalancing
                    edgeThreshold = rangeSize * 0.1
                    if distanceFromLower < edgeThreshold or distanceFromUpper < edgeThreshold:
                        logging.info(
                            f'[REBALANCE_WORKER] Position {position.tokenId} is near edge - '
                            f'distance from lower: {distanceFromLower}, from upper: {distanceFromUpper}, '
                            f'threshold: {edgeThreshold}'
                        )
                        needsRebalance = True
                        break

                if needsRebalance:
                    logging.info(f'[REBALANCE_WORKER] Triggering rebalance for agent {agent_id}')
                    await appManager.deposit_made_to_agent(userId=user_id, agentId=agent_id)
                    logging.info(f'[REBALANCE_WORKER] Successfully rebalanced agent {agent_id}')
                else:
                    logging.info(f'[REBALANCE_WORKER] Agent {agent_id} positions are in range, no rebalance needed')

            except Exception as error:
                logging.error(f'[REBALANCE_WORKER] Error checking agent {agent_id}: {error}')
                logging.exception(error)
                continue

        duration = time.time() - startTime
        logging.info(f'[REBALANCE_WORKER] Completed agent rebalance check in {duration:.2f}s')

    except Exception as error:
        logging.error(f'[REBALANCE_WORKER] Error in rebalance worker: {error}')
        logging.exception(error)
    finally:
        await appManager.database.disconnect()


async def main() -> None:
    logging.info('[REBALANCE_WORKER] Starting rebalance worker')

    scheduler = AsyncIOScheduler()

    # Run every 15 minutes
    trigger = IntervalTrigger(
        minutes=15,
        start_date=datetime.datetime.now(tz=datetime.UTC),
    )

    scheduler.add_job(
        func=check_and_rebalance_agents,
        trigger=trigger,
        id='rebalance-agents',
        name='rebalance-agents',
        replace_existing=True,
    )

    scheduler.start()
    logging.info('[REBALANCE_WORKER] Scheduler started, checking agents every 15 minutes')

    # Run once immediately on startup
    logging.info('[REBALANCE_WORKER] Running initial check')
    await check_and_rebalance_agents()

    # Keep the worker running
    event = asyncio.Event()
    try:
        await event.wait()
    finally:
        logging.info('[REBALANCE_WORKER] Shutting down scheduler...')
        scheduler.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
