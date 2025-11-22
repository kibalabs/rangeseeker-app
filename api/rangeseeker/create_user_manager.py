import os

from core.requester import Requester
from core.store.database import Database

from rangeseeker.app_manager import AppManager
from rangeseeker.external.amp_client import AmpClient
from rangeseeker.external.coinbase_cdp_client import CoinbaseCdpClient
from rangeseeker.external.gemini_llm import GeminiLLM
from rangeseeker.external.uniswap_data_client import UniswapDataClient
from rangeseeker.strategy_manager import StrategyManager
from rangeseeker.strategy_parser import StrategyParser
from rangeseeker.user_manager import UserManager

DB_HOST = os.environ['DB_HOST']
DB_PORT = os.environ['DB_PORT']
DB_NAME = os.environ['DB_NAME']
DB_USERNAME = os.environ['DB_USERNAME']
DB_PASSWORD = os.environ['DB_PASSWORD']


def create_app_manager() -> AppManager:
    database = Database(
        connectionString=Database.create_psql_connection_string(
            host=DB_HOST,
            port=DB_PORT,
            name=DB_NAME,
            username=DB_USERNAME,
            password=DB_PASSWORD,
        )
    )
    requester = Requester()
    ampToken = os.environ.get('THEGRAPHAMP_API_KEY', '')
    geminiApiKey = os.environ.get('GEMINI_API_KEY', '')
    ampClient = AmpClient(flightUrl='https://gateway.amp.staging.thegraph.com', token=ampToken)
    uniswapClient = UniswapDataClient(ampClient=ampClient)
    geminiLlm = GeminiLLM(apiKey=geminiApiKey, requester=requester)
    parser = StrategyParser(llm=geminiLlm)
    coinbaseCdpClient = CoinbaseCdpClient(
        requester=requester,
        walletSecret=os.environ['COINBASE_CDP_WALLET_SECRET'],
        apiKeyName=os.environ['COINBASE_CDP_API_KEY_NAME'],
        apiKeyPrivateKey=os.environ['COINBASE_CDP_API_KEY_PRIVATE_KEY'],
    )
    userManager = UserManager(
        database=database,
        coinbaseCdpClient=coinbaseCdpClient,
    )
    strategyManager = StrategyManager(database=database, uniswapClient=uniswapClient, parser=parser)
    appManager = AppManager(
        database=database,
        userManager=userManager,
        strategyManager=strategyManager,
    )
    return appManager
