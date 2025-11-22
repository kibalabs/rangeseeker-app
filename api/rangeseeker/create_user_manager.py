import os

from core.store.database import Database

from rangeseeker.app_manager import AppManager
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
    userManager = UserManager(database=database)
    appManager = AppManager(database=database, userManager=userManager)
    return appManager
