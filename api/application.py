import os

from core import logging
from core.api.default_routes import create_default_routes
from core.api.middleware.database_connection_middleware import DatabaseConnectionMiddleware
from core.api.middleware.exception_handling_middleware import ExceptionHandlingMiddleware
from core.api.middleware.logging_middleware import LoggingMiddleware
from core.api.middleware.server_headers_middleware import ServerHeadersMiddleware
from core.util.value_holder import RequestIdHolder
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import Mount

from rangeseeker.api.v1_api import create_v1_routes
from rangeseeker.create_user_manager import create_app_manager

name = os.environ.get('NAME', 'rangeseeker-api')
version = os.environ.get('VERSION', 'local')
environment = os.environ.get('ENV', 'dev')
isRunningDebugMode = environment == 'dev'

requestIdHolder = RequestIdHolder()
if isRunningDebugMode:
    logging.init_basic_logging()
else:
    logging.init_json_logging(name=name, version=version, environment=environment, requestIdHolder=requestIdHolder)
logging.init_external_loggers(loggerNames=['httpx'])

appManager = create_app_manager()


async def startup() -> None:
    await appManager.database.connect()


async def shutdown() -> None:
    await appManager.database.disconnect()


app = Starlette(
    routes=[
        *create_default_routes(name=name, version=version, environment=environment),
        Mount(
            path='/v1',
            routes=create_v1_routes(appManager=appManager),
        ),
    ],
    on_startup=[startup],
    on_shutdown=[shutdown],
)
app.add_middleware(ExceptionHandlingMiddleware)
app.add_middleware(ServerHeadersMiddleware, name=name, version=version, environment=environment)
app.add_middleware(LoggingMiddleware, requestIdHolder=requestIdHolder)
app.add_middleware(DatabaseConnectionMiddleware, database=appManager.database)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=9)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['*'],
    allow_origins=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_origin_regex='https://.*\\.?(tokenpage.xyz)',
)
