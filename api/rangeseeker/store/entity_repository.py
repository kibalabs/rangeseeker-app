import dataclasses
import typing
import uuid
from collections.abc import Sequence

import sqlalchemy
from core.exceptions import KibaException
from core.exceptions import NotFoundException
from core.store.database import Database
from core.store.database import DatabaseConnection
from core.store.retriever import FieldFilter
from core.store.retriever import Order
from core.util import chain_util
from core.util import date_util
from pydantic import BaseModel
from sqlalchemy.dialects import postgresql as sqlalchemy_psql
from sqlalchemy.engine import Result
from sqlalchemy.engine import RowMapping

UNDEFINED = '___UNDEFINED___'

EntityType = typing.TypeVar('EntityType', bound=BaseModel)


@dataclasses.dataclass
class UUIDFieldFilter(FieldFilter):
    eq: uuid.UUID | str | None = None
    ne: uuid.UUID | str | None = None
    containedIn: Sequence[uuid.UUID | str] | None = None
    notContainedIn: Sequence[uuid.UUID | str] | None = None


@dataclasses.dataclass
class StringFieldFilter(FieldFilter):
    eq: str | None = None
    ne: str | None = None
    containedIn: Sequence[str] | None = None
    notContainedIn: Sequence[str] | None = None


class EntityRepository(typing.Generic[EntityType]):
    def __init__(
        self,
        table: sqlalchemy.Table,
        modelClass: type[EntityType],
    ) -> None:
        self.table = table
        self.modelClass = modelClass
        try:
            self.idColumn = next(column for column in table.columns if column.primary_key)
        except StopIteration:
            raise KibaException(f'Failed to find id column for table: {table.name}')

    def _convert_value_from_db(self, column: sqlalchemy.Column[typing.Any], value: typing.Any | None) -> typing.Any | None:
        if value is None:
            return None
        if isinstance(column.type, sqlalchemy_psql.UUID):
            value = str(value)
        if isinstance(column.type, sqlalchemy.DateTime):
            value = date_util.datetime_to_utc(dt=value)
        if column.key.lower().endswith('address'):
            value = chain_util.normalize_address(value=value)
        return value

    def _convert_value_to_db(self, column: sqlalchemy.Column[typing.Any], value: typing.Any | None) -> typing.Any | None:
        if value is None:
            return None
        if isinstance(column.type, sqlalchemy_psql.UUID):
            value = uuid.UUID(value) if isinstance(value, str) else value
        if isinstance(column.type, sqlalchemy.DateTime):
            value = date_util.datetime_to_utc_naive_datetime(dt=value)
        if isinstance(column.type, sqlalchemy.JSON) and isinstance(value, BaseModel):
            value = value.model_dump()
        if column.key.lower().endswith('address'):
            value = chain_util.normalize_address(value=value)
        return value

    def from_row(self, row: RowMapping) -> EntityType:
        fieldValues = {}
        for column in self.table.columns:
            fieldValues[column.key] = self._convert_value_from_db(column=column, value=row[column])
        return self.modelClass.model_validate(fieldValues)

    async def get_one(
        self,
        database: Database | DatabaseConnection,
        fieldFilters: list[FieldFilter] | None = None,
    ) -> EntityType:
        result = await self._execute_get_query(database=database, fieldFilters=fieldFilters, limit=1)
        row = result.mappings().first()
        if row is None:
            raise NotFoundException
        return self.from_row(row=row)

    async def get_one_or_none(
        self,
        database: Database | DatabaseConnection,
        fieldFilters: list[FieldFilter] | None = None,
    ) -> EntityType | None:
        result = await self._execute_get_query(database=database, fieldFilters=fieldFilters, limit=1)
        row = result.mappings().first()
        return self.from_row(row=row) if row else None

    async def get_first(
        self,
        database: Database | DatabaseConnection,
        fieldFilters: list[FieldFilter] | None = None,
    ) -> EntityType | None:
        return await self.get_one_or_none(database=database, fieldFilters=fieldFilters)

    async def list_many(
        self,
        database: Database | DatabaseConnection,
        fieldFilters: list[FieldFilter] | None = None,
        orders: list[Order] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EntityType]:
        result = await self._execute_get_query(
            database=database,
            fieldFilters=fieldFilters,
            orders=orders,
            limit=limit,
            offset=offset,
        )
        return [self.from_row(row=row) for row in result.mappings()]

    async def create(
        self,
        database: Database | DatabaseConnection,
        **kwargs: typing.Any,
    ) -> EntityType:
        now = date_util.datetime_from_now()
        values = {
            'createdDate': now,
            'updatedDate': now,
        }
        for key, value in kwargs.items():
            if value is UNDEFINED:
                continue
            column = self.table.columns.get(key)
            if column is None:
                raise KibaException(f'Column {key} not found in table {self.table.name}')
            values[key] = self._convert_value_to_db(column=column, value=value)

        if self.idColumn.key not in values:
            if isinstance(self.idColumn.type, sqlalchemy_psql.UUID):
                values[self.idColumn.key] = uuid.uuid4()

        query = self.table.insert().values(**values).returning(*self.table.columns)
        result = await database.execute(query=query)
        row = result.mappings().first()
        if row is None:
            raise KibaException('Failed to create entity')
        return self.from_row(row=row)

    async def update(
        self,
        database: Database | DatabaseConnection,
        **kwargs: typing.Any,
    ) -> EntityType:
        now = date_util.datetime_from_now()
        idValue = kwargs.pop(self.idColumn.key, None)
        if idValue is None:
            raise KibaException(f'ID field {self.idColumn.key} is required for update')

        values = {'updatedDate': now}
        for key, value in kwargs.items():
            if value is UNDEFINED:
                continue
            column = self.table.columns.get(key)
            if column is None:
                raise KibaException(f'Column {key} not found in table {self.table.name}')
            values[key] = self._convert_value_to_db(column=column, value=value)

        query = (
            self.table.update()
            .where(self.idColumn == self._convert_value_to_db(column=self.idColumn, value=idValue))
            .values(**values)
            .returning(*self.table.columns)
        )
        result = await database.execute(query=query)
        row = result.mappings().first()
        if row is None:
            raise NotFoundException
        return self.from_row(row=row)

    async def _execute_get_query(
        self,
        database: Database | DatabaseConnection,
        fieldFilters: list[FieldFilter] | None = None,
        orders: list[Order] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Result[typing.Any]:
        query = sqlalchemy.select(*self.table.columns)

        if fieldFilters:
            for fieldFilter in fieldFilters:
                column = self.table.columns.get(fieldFilter.fieldName)
                if column is None:
                    raise KibaException(f'Column {fieldFilter.fieldName} not found')
                query = self._apply_field_filter(query=query, column=column, fieldFilter=fieldFilter)

        if orders:
            for order in orders:
                column = self.table.columns.get(order.fieldName)
                if column is None:
                    raise KibaException(f'Column {order.fieldName} not found')
                query = query.order_by(column.desc() if order.direction.value == 'descending' else column.asc())

        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        return await database.execute(query=query)

    def _apply_field_filter(
        self,
        query: sqlalchemy.Select,
        column: sqlalchemy.Column[typing.Any],
        fieldFilter: FieldFilter,
    ) -> sqlalchemy.Select:
        if isinstance(fieldFilter, UUIDFieldFilter):
            if fieldFilter.eq is not None:
                value = self._convert_value_to_db(column=column, value=fieldFilter.eq)
                query = query.where(column == value)
            if fieldFilter.ne is not None:
                value = self._convert_value_to_db(column=column, value=fieldFilter.ne)
                query = query.where(column != value)
            if fieldFilter.containedIn is not None:
                values = [self._convert_value_to_db(column=column, value=v) for v in fieldFilter.containedIn]
                query = query.where(column.in_(values))
            if fieldFilter.notContainedIn is not None:
                values = [self._convert_value_to_db(column=column, value=v) for v in fieldFilter.notContainedIn]
                query = query.where(column.notin_(values))
        elif isinstance(fieldFilter, StringFieldFilter):
            if fieldFilter.eq is not None:
                query = query.where(column == fieldFilter.eq)
            if fieldFilter.ne is not None:
                query = query.where(column != fieldFilter.ne)
            if fieldFilter.containedIn is not None:
                query = query.where(column.in_(fieldFilter.containedIn))
            if fieldFilter.notContainedIn is not None:
                query = query.where(column.notin_(fieldFilter.notContainedIn))
        return query
