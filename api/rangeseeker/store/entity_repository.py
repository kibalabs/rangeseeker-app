import dataclasses
import typing
import uuid
from collections.abc import Sequence

import sqlalchemy
from core.exceptions import KibaException
from core.exceptions import NotFoundException
from core.store.database import Database
from core.store.database import DatabaseConnection
from core.store.database import ResultType
from core.store.retriever import BooleanFieldFilter
from core.store.retriever import DateFieldFilter
from core.store.retriever import Direction
from core.store.retriever import FieldFilter
from core.store.retriever import FloatFieldFilter
from core.store.retriever import IntegerFieldFilter
from core.store.retriever import Order
from core.store.retriever import RandomOrder
from core.store.retriever import StringFieldFilter
from core.util import chain_util
from core.util import date_util
from pydantic import BaseModel
from sqlalchemy import Table
from sqlalchemy.dialects import postgresql as sqlalchemy_psql
from sqlalchemy.engine import Result
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql import Select

UNDEFINED = '___UNDEFINED___'

EntityType = typing.TypeVar('EntityType', bound=BaseModel)


@dataclasses.dataclass
class UUIDFieldFilter(FieldFilter):
    eq: uuid.UUID | str | None = None
    ne: uuid.UUID | str | None = None
    containedIn: Sequence[uuid.UUID | str] | None = None
    notContainedIn: Sequence[uuid.UUID | str] | None = None


def _uuid_from_value(value: uuid.UUID | str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(hex=value)


# NOTE(krishan711): i think the logical extension of this would be to have a "KibaTable(sqlalchemy.Table) class"
class EntityRepository(typing.Generic[EntityType]):  # noqa: UP046
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

    def _convert_value_from_db(self, column: sqlalchemy.Column[typing.Any], value: typing.Any | None) -> typing.Any | None:  # type: ignore[explicit-any]
        if value is None:
            return None
        if isinstance(column.type, sqlalchemy_psql.UUID):
            value = str(value)
        if isinstance(column.type, sqlalchemy.DateTime):
            value = date_util.datetime_to_utc(dt=value)  # type: ignore[arg-type]
        # NOTE(krishan711): need a special type for addresses
        if column.key.lower().endswith('address'):
            value = chain_util.normalize_address(value=value)  # type: ignore[arg-type]
        return value

    def _convert_value_to_db(self, column: sqlalchemy.Column[typing.Any], value: typing.Any | None) -> typing.Any | None:  # type: ignore[explicit-any]
        if value is None:
            return None
        if isinstance(column.type, sqlalchemy_psql.UUID):
            value = uuid.UUID(value)
        if isinstance(column.type, sqlalchemy.DateTime):
            value = date_util.datetime_to_utc_naive_datetime(dt=value)  # type: ignore[arg-type]
        if isinstance(column.type, sqlalchemy.JSON) and isinstance(value, BaseModel):
            value = value.model_dump()
        # NOTE(krishan711): need a special type for addresses
        if column.key.lower().endswith('address'):
            value = chain_util.normalize_address(value=value)  # type: ignore[arg-type]
        return value

    def from_row(self, row: RowMapping) -> EntityType:
        fieldValues = {}
        for column in self.table.columns:
            fieldValues[column.key] = self._convert_value_from_db(column=column, value=row[column])
        return self.modelClass.model_validate(fieldValues)

    def force_from_result(self, result: Result[typing.Any]) -> EntityType:  # type: ignore[explicit-any]
        row = result.mappings().first()
        if row is None:
            raise NotFoundException
        return self.from_row(row=row)

    def _validate_kwargs(self, keys: list[str]) -> None:
        validColumnName = {column.key for column in self.table.columns}
        for key in keys:
            if key not in validColumnName:
                raise KibaException(f'Unknown column: {key}. Valid columns are: {", ".join(validColumnName)}')

    def _create_values(self, kwargs: dict[str, typing.Any], should_add_created_date: bool = False, should_add_updated_date: bool = False) -> dict[sqlalchemy.Column[typing.Any], typing.Any]:  # type: ignore[explicit-any]
        currentDate = date_util.datetime_from_now()
        self._validate_kwargs(keys=list(kwargs.keys()))
        values: dict[sqlalchemy.Column[typing.Any], typing.Any] = {}  # type: ignore[explicit-any]
        if should_add_created_date:
            values[self.table.c.createdDate] = self._convert_value_to_db(column=self.table.c.createdDate, value=currentDate)
        if should_add_updated_date:
            values[self.table.c.updatedDate] = self._convert_value_to_db(column=self.table.c.updatedDate, value=currentDate)
        for key, value in kwargs.items():
            column = getattr(self.table.c, key, None)
            if column is None:
                raise KibaException(f'Unknown column: {key}. Valid columns are: {", ".join({column.key for column in self.table.columns})}')
            values[column] = self._convert_value_to_db(column=column, value=value)
        return values

    async def create(self, database: Database, connection: DatabaseConnection | None = None, **kwargs) -> EntityType:  # type: ignore[no-untyped-def]  # noqa: ANN003
        createValues = self._create_values(kwargs=kwargs, should_add_created_date=True, should_add_updated_date=True)
        if isinstance(self.idColumn.type, sqlalchemy_psql.UUID) and self.idColumn not in createValues:
            createValues[self.idColumn] = uuid.uuid4()
        result = await database.execute(query=self.table.insert().values(createValues).returning(self.table), connection=connection)
        return self.force_from_result(result=result)

    async def update(self, database: Database, connection: DatabaseConnection | None = None, **kwargs) -> EntityType:  # type: ignore[no-untyped-def]  # noqa: ANN003
        updateValues = self._create_values(kwargs=kwargs, should_add_updated_date=True)
        idValue: typing.Any | None = updateValues.pop(self.idColumn)  # type: ignore[explicit-any]
        if idValue is None:
            raise KibaException(f'Failed to find id value for update to {self.table}')
        result = await database.execute(query=self.table.update().where(self.idColumn == idValue).values(updateValues).returning(self.table), connection=connection)
        return self.force_from_result(result=result)

    async def upsert(self, database: Database, constraintColumnNames: list[str], connection: DatabaseConnection | None = None, **kwargs) -> EntityType:  # type: ignore[no-untyped-def]  # noqa: ANN003
        updateValues = self._create_values(kwargs=kwargs, should_add_updated_date=True, should_add_created_date=False)
        insertValues = self._create_values(kwargs=kwargs, should_add_updated_date=True, should_add_created_date=True)
        if isinstance(self.idColumn.type, sqlalchemy_psql.UUID) and self.idColumn not in insertValues:
            insertValues[self.idColumn] = uuid.uuid4()
        insertStatement = sqlalchemy_psql.insert(self.table).values(insertValues)
        constraintColumns = [getattr(self.table.c, columnName) for columnName in constraintColumnNames]
        doUpdateStatement = insertStatement.on_conflict_do_update(
            index_elements=constraintColumns,
            set_=updateValues,
        )
        result = await database.execute(query=doUpdateStatement.returning(self.table), connection=connection)
        return self.force_from_result(result=result)

    async def delete(self, database: Database, fieldFilters: list[FieldFilter], connection: DatabaseConnection | None = None) -> None:
        query = self.table.delete()
        # NOTE(krishan711): need to fix typing properly here
        query = self._apply_field_filters(query=query, table=self.table, fieldFilters=fieldFilters)  # type: ignore[assignment, arg-type]
        await database.execute(query=query, connection=connection)  # type: ignore[arg-type]

    # Reading

    def _apply_order(self, query: Select[ResultType], table: Table, order: Order) -> Select[ResultType]:
        if isinstance(order, RandomOrder):
            query = query.order_by(sqlalchemy.sql.functions.random())
        else:
            field = table.c[order.fieldName]
            query = query.order_by(field.asc() if order.direction == Direction.ASCENDING else field.desc())
        return query

    def _apply_orders(self, query: Select[ResultType], table: Table, orders: Sequence[Order]) -> Select[ResultType]:
        for order in orders:
            query = self._apply_order(query=query, table=table, order=order)
        return query

    def _apply_string_field_filter(self, query: Select[ResultType], table: Table, fieldFilter: StringFieldFilter) -> Select[ResultType]:
        field = table.c[fieldFilter.fieldName]
        if fieldFilter.eq is not None:
            query = query.where(field == fieldFilter.eq)
        if fieldFilter.ne is not None:
            query = query.where(field != fieldFilter.ne)
        if fieldFilter.containedIn is not None:
            query = query.where(field.in_(fieldFilter.containedIn))
        if fieldFilter.notContainedIn is not None:
            query = query.where(field.not_in(fieldFilter.notContainedIn))
        return query

    def _apply_uuid_field_filter(self, query: Select[ResultType], table: Table, fieldFilter: UUIDFieldFilter) -> Select[ResultType]:
        field = table.c[fieldFilter.fieldName]
        if fieldFilter.eq is not None:
            query = query.where(field == _uuid_from_value(value=fieldFilter.eq))
        if fieldFilter.ne is not None:
            query = query.where(field != _uuid_from_value(value=fieldFilter.ne))
        if fieldFilter.containedIn is not None:
            query = query.where(field.in_([_uuid_from_value(value=value) for value in fieldFilter.containedIn]))
        if fieldFilter.notContainedIn is not None:
            query = query.where(field.not_in([_uuid_from_value(value=value) for value in fieldFilter.notContainedIn]))
        return query

    def _apply_date_field_filter(self, query: Select[ResultType], table: Table, fieldFilter: DateFieldFilter) -> Select[ResultType]:
        field = table.c[fieldFilter.fieldName]
        if fieldFilter.eq is not None:
            query = query.where(field == date_util.datetime_to_utc_naive_datetime(fieldFilter.eq))
        if fieldFilter.ne is not None:
            query = query.where(field != date_util.datetime_to_utc_naive_datetime(fieldFilter.ne))
        if fieldFilter.lte is not None:
            query = query.where(field <= date_util.datetime_to_utc_naive_datetime(fieldFilter.lte))
        if fieldFilter.lt is not None:
            query = query.where(field < date_util.datetime_to_utc_naive_datetime(fieldFilter.lt))
        if fieldFilter.gte is not None:
            query = query.where(field >= date_util.datetime_to_utc_naive_datetime(fieldFilter.gte))
        if fieldFilter.gt is not None:
            query = query.where(field > date_util.datetime_to_utc_naive_datetime(fieldFilter.gt))
        if fieldFilter.containedIn is not None:
            query = query.where(field.in_([date_util.datetime_to_utc_naive_datetime(value) for value in fieldFilter.containedIn]))
        if fieldFilter.notContainedIn is not None:
            query = query.where(field.not_in([date_util.datetime_to_utc_naive_datetime(value) for value in fieldFilter.notContainedIn]))
        return query

    def _apply_integer_field_filter(self, query: Select[ResultType], table: Table, fieldFilter: IntegerFieldFilter) -> Select[ResultType]:
        field = table.c[fieldFilter.fieldName]
        if fieldFilter.eq is not None:
            query = query.where(field == fieldFilter.eq)
        if fieldFilter.ne is not None:
            query = query.where(field != fieldFilter.ne)
        if fieldFilter.lte is not None:
            query = query.where(field <= fieldFilter.lte)
        if fieldFilter.lt is not None:
            query = query.where(field < fieldFilter.lt)
        if fieldFilter.gte is not None:
            query = query.where(field >= fieldFilter.gte)
        if fieldFilter.gt is not None:
            query = query.where(field > fieldFilter.gt)
        if fieldFilter.containedIn is not None:
            query = query.where(field.in_(fieldFilter.containedIn))
        if fieldFilter.notContainedIn is not None:
            query = query.where(field.not_in(fieldFilter.notContainedIn))
        return query

    def _apply_float_field_filter(self, query: Select[ResultType], table: Table, fieldFilter: FloatFieldFilter) -> Select[ResultType]:
        field = table.c[fieldFilter.fieldName]
        if fieldFilter.eq is not None:
            query = query.where(field == fieldFilter.eq)
        if fieldFilter.ne is not None:
            query = query.where(field != fieldFilter.ne)
        if fieldFilter.lte is not None:
            query = query.where(field <= fieldFilter.lte)
        if fieldFilter.lt is not None:
            query = query.where(field < fieldFilter.lt)
        if fieldFilter.gte is not None:
            query = query.where(field >= fieldFilter.gte)
        if fieldFilter.gt is not None:
            query = query.where(field > fieldFilter.gt)
        if fieldFilter.containedIn is not None:
            query = query.where(field.in_(fieldFilter.containedIn))
        if fieldFilter.notContainedIn is not None:
            query = query.where(field.not_in(fieldFilter.notContainedIn))
        return query

    def _apply_boolean_field_filter(self, query: Select[ResultType], table: Table, fieldFilter: BooleanFieldFilter) -> Select[ResultType]:
        field = table.c[fieldFilter.fieldName]
        if fieldFilter.eq is not None:
            query = query.where(field == fieldFilter.eq)
        if fieldFilter.ne is not None:
            query = query.where(field != fieldFilter.ne)
        return query

    def _apply_field_filter(self, query: Select[ResultType], table: Table, fieldFilter: FieldFilter) -> Select[ResultType]:
        field = table.c[fieldFilter.fieldName]
        if fieldFilter.isNull:
            query = query.where(field.is_(None))
        if fieldFilter.isNotNull:
            query = query.where(field.is_not(None))
        if isinstance(fieldFilter, StringFieldFilter):
            query = self._apply_string_field_filter(query=query, table=table, fieldFilter=fieldFilter)
        if isinstance(fieldFilter, DateFieldFilter):
            query = self._apply_date_field_filter(query=query, table=table, fieldFilter=fieldFilter)
        if isinstance(fieldFilter, IntegerFieldFilter):
            query = self._apply_integer_field_filter(query=query, table=table, fieldFilter=fieldFilter)
        if isinstance(fieldFilter, FloatFieldFilter):
            query = self._apply_float_field_filter(query=query, table=table, fieldFilter=fieldFilter)
        if isinstance(fieldFilter, BooleanFieldFilter):
            query = self._apply_boolean_field_filter(query=query, table=table, fieldFilter=fieldFilter)
        if isinstance(fieldFilter, UUIDFieldFilter):
            query = self._apply_uuid_field_filter(query=query, table=table, fieldFilter=fieldFilter)
        return query

    def _apply_field_filters(self, query: Select[ResultType], table: Table, fieldFilters: Sequence[FieldFilter]) -> Select[ResultType]:
        for fieldFilter in fieldFilters:
            query = self._apply_field_filter(query=query, table=table, fieldFilter=fieldFilter)
        return query

    async def list_many(self, database: Database, fieldFilters: list[FieldFilter] | None = None, orders: list[Order] | None = None, limit: int | None = None, offset: int | None = None, connection: DatabaseConnection | None = None) -> list[EntityType]:
        query = self.table.select()
        if fieldFilters is not None:
            query = self._apply_field_filters(query=query, table=self.table, fieldFilters=fieldFilters)
        if orders is not None:
            query = self._apply_orders(query=query, table=self.table, orders=orders)
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        result = await database.execute(query=query, connection=connection)
        return [self.from_row(row=row) for row in result.mappings()]

    async def get_first(self, database: Database, fieldFilters: list[FieldFilter] | None = None, orders: list[Order] | None = None, connection: DatabaseConnection | None = None) -> EntityType | None:
        query = self.table.select()
        if fieldFilters is not None:
            query = self._apply_field_filters(query=query, table=self.table, fieldFilters=fieldFilters)
        if orders is not None:
            query = self._apply_orders(query=query, table=self.table, orders=orders)
        query = query.limit(1)
        result = await database.execute(query=query, connection=connection)
        return next((self.from_row(row=row) for row in result.mappings()), None)

    async def get(self, database: Database, idValue: typing.Any, connection: DatabaseConnection | None = None) -> EntityType:  # type: ignore[explicit-any]
        query = self.table.select().where(self.idColumn == idValue)
        result = await database.execute(query=query, connection=connection)
        # TODO(krishan711): raise an exception if there is more than one result
        return self.force_from_result(result=result)

    async def get_one(self, database: Database, fieldFilters: list[FieldFilter], connection: DatabaseConnection | None = None) -> EntityType:
        query = self.table.select()
        query = self._apply_field_filters(query=query, table=self.table, fieldFilters=fieldFilters)
        result = await database.execute(query=query, connection=connection)
        # TODO(krishan711): raise an exception if there is more than one result
        return self.force_from_result(result=result)

    async def get_one_or_none(self, database: Database, fieldFilters: list[FieldFilter], connection: DatabaseConnection | None = None) -> EntityType | None:
        try:
            return await self.get_one(database=database, fieldFilters=fieldFilters, connection=connection)
        except NotFoundException:
            return None
