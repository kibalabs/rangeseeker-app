from collections.abc import AsyncIterator
from datetime import datetime
from typing import Union

import adbc_driver_flightsql.dbapi as flight_sql

# Arrow/Flight SQL types that can be returned in query results
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
    """Client for querying TheGraph AMP hosted datasets via Arrow Flight SQL."""

    def __init__(self, flightUrl: str, token: str | None = None) -> None:
        """
        Initialize AMP client.

        Args:
            flightUrl: Arrow Flight SQL endpoint URL (e.g., "https://gateway.amp.staging.thegraph.com")
            token: Optional bearer token for authentication
        """
        self.flightUrl = flightUrl
        self.token = token

    async def execute_sql(self, sql: str) -> AsyncIterator[dict[str, SqlValue]]:
        """
        Execute SQL query against AMP dataset using ADBC Flight SQL.

        Streams results one row at a time as they are fetched from the server.

        Args:
            sql: SQL query string to execute

        Yields:
            Dictionary mapping column names to values for each row

        Raises:
            Exception: If query execution fails
        """

        # ADBC Flight SQL connection requires specific parameter format
        # The URI parameter must be passed positionally, not in db_kwargs
        connKwargs = {
            'db_kwargs': {
                'adbc.flight.sql.client_option.tls_skip_verify': 'false',
            }
        }

        if self.token:
            connKwargs['db_kwargs']['adbc.flight.sql.authorization_header'] = f'Bearer {self.token}'

        # Execute query and stream results
        with flight_sql.connect(self.flightUrl, **connKwargs) as conn, conn.cursor() as cursor:
            cursor.execute(sql)

            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Stream rows one at a time
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                yield dict(zip(columns, row, strict=True))
