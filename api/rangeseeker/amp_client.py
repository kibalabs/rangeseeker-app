from collections.abc import AsyncIterator
from datetime import datetime
from typing import Union

import adbc_driver_flightsql.dbapi as flight_sql

SqlValue = Union[
    None,
    bool,
    int,
    float,
    str,
    bytes,
    datetime,
]


class AmpClient:
    def __init__(self, flightUrl: str, token: str) -> None:
        self.flightUrl = flightUrl
        self.token = token

    async def execute_sql(self, sql: str) -> AsyncIterator[dict[str, SqlValue]]:
        connKwargs = {
            'db_kwargs': {
                'adbc.flight.sql.client_option.tls_skip_verify': 'false',
                'adbc.flight.sql.authorization_header': f'Bearer {self.token}',
            }
        }
        with flight_sql.connect(self.flightUrl, **connKwargs) as conn, conn.cursor() as cursor:
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                yield dict(zip(columns, row, strict=True))
