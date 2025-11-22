from core.store.database import Database
from core.util import json_util

from rangeseeker.model import Strategy
from rangeseeker.store import schema
from rangeseeker.store.entity_repository import UUIDFieldFilter
from rangeseeker.strategy_parser import StrategyDefinition
from rangeseeker.strategy_parser import StrategyParser
from rangeseeker.uniswap_data_client import UniswapDataClient

POOL_ADDRESS = '0xd0b53D9277642d899DF5C87A3966A349A798F224'


class StrategyManager:
    def __init__(self, database: Database, uniswapClient: UniswapDataClient, parser: StrategyParser) -> None:
        self.database = database
        self.uniswapClient = uniswapClient
        self.parser = parser

    async def parse_strategy(self, description: str) -> StrategyDefinition:
        currentPrice = await self.uniswapClient.get_current_price(POOL_ADDRESS)
        volatility = await self.uniswapClient.get_pool_volatility(POOL_ADDRESS, hoursBack=24)
        contextData: dict[str, float | str | None] = {
            'currentPrice': currentPrice,
            'volatility': volatility,
        }
        return await self.parser.parse(description=description, contextData=contextData)

    async def create_strategy(self, userId: str, name: str, description: str, strategyDefinition: StrategyDefinition) -> Strategy:
        rulesJson = json_util.loads(json_util.dumps([rule.model_dump() for rule in strategyDefinition.rules]))
        strategy = await schema.StrategiesRepository.create(
            database=self.database,
            userId=userId,
            name=name,
            description=description,
            rulesJson=rulesJson,
            feedRequirements=strategyDefinition.feedRequirements,
            summary=strategyDefinition.summary,
        )
        return strategy

    async def get_strategy(self, strategyId: str) -> Strategy:
        return await schema.StrategiesRepository.get_one(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.StrategiesTable.c.strategyId.key, eq=strategyId)],
        )

    async def list_user_strategies(self, userId: str) -> list[Strategy]:
        return await schema.StrategiesRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName=schema.StrategiesTable.c.userId.key, eq=userId)],
        )
