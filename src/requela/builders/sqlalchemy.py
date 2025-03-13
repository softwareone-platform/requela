from collections.abc import Callable, Sequence
from datetime import date, datetime

from sqlalchemy import (
    BooleanClauseList,
    ColumnElement,
    ColumnExpressionArgument,
    Exists,
    UnaryExpression,
    and_,
    exists,
    or_,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Query, aliased

from requela.builders.base import QueryBuilder
from requela.dataclasses import FilterExpression, JoinExpression, OrderByExpression


class SQLAlchemyQueryBuilder(QueryBuilder):
    def __init__(
        self,
        model_class: DeclarativeBase,
        resolve_alias_callback: Callable | None = None,
        validate_operator_and_field_callback: Callable | None = None,
        validate_ordering_callback: Callable | None = None,
    ):
        super().__init__(
            model_class,
            resolve_alias_callback=resolve_alias_callback,
            validate_operator_and_field_callback=validate_operator_and_field_callback,
            validate_ordering_callback=validate_ordering_callback,
        )
        self.joins: list[JoinExpression] = []

    def get_initial_query(self):
        return select(self.model_class)

    def get_field_type(self, field: str) -> type:
        field_type = getattr(self.model_class, field).property.columns[0].type.python_type
        return field_type

    def apply_and(self, *conditions: ColumnExpressionArgument) -> ColumnElement:
        return and_(*conditions)

    def apply_or(self, *conditions: ColumnExpressionArgument) -> ColumnElement:
        return or_(*conditions)

    def apply_not(self, condition: ColumnElement) -> ColumnElement:
        return ~condition

    def apply_eq(
        self, prop: str, value: str | bool | date | datetime | int | float | None
    ) -> ColumnExpressionArgument:
        if value is True or value is False or value is None:
            return self.resolve_property(prop).is_(value)
        return self.resolve_property(prop) == value

    def apply_ne(
        self, prop: str, value: str | bool | date | datetime | int | float | None
    ) -> ColumnExpressionArgument:
        if value is True or value is False or value is None:
            return self.resolve_property(prop).isnot(value)
        return self.resolve_property(prop) != value

    def apply_gt(self, prop: str, value: date | datetime | int | float) -> ColumnExpressionArgument:
        return self.resolve_property(prop) > value

    def apply_lt(self, prop: str, value: date | datetime | int | float) -> ColumnExpressionArgument:
        return self.resolve_property(prop) < value

    def apply_gte(
        self, prop: str, value: date | datetime | int | float
    ) -> ColumnExpressionArgument:
        return self.resolve_property(prop) >= value

    def apply_lte(
        self, prop: str, value: date | datetime | int | float
    ) -> ColumnExpressionArgument:
        return self.resolve_property(prop) <= value

    def apply_in(
        self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]
    ) -> ColumnExpressionArgument:
        return self.resolve_property(prop).in_(value)

    def apply_out(
        self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]
    ) -> ColumnExpressionArgument:
        return self.resolve_property(prop).not_in(value)

    def apply_like(self, prop: str, value: str) -> ColumnExpressionArgument:
        sql_pattern = value.replace("*", "%")
        return self.resolve_property(prop).like(sql_pattern)

    def apply_ilike(self, prop: str, value: str) -> ColumnExpressionArgument:
        sql_pattern = value.replace("*", "%")
        return self.resolve_property(prop).ilike(sql_pattern)

    def resolve_property(self, prop_path: str) -> UnaryExpression:
        prop_path = self.resolve_alias(prop_path)
        model = self.model_class
        parts = prop_path.split(".")

        if len(parts) > 1:
            current = model

            for part in parts[:-1]:
                relationship = getattr(current, part)
                target_model = relationship.property.mapper.class_
                alias = aliased(target_model)

                if not relationship.property.uselist:
                    is_nullable = any(
                        column.nullable for column in relationship.property.local_columns
                    )
                    self.joins.append(
                        JoinExpression(target=alias, on=relationship, is_outer=is_nullable)
                    )
                current = alias

            return getattr(current, parts[-1])

        return getattr(model, prop_path)

    def apply_any(
        self, relationship_name, condition: ColumnElement | ColumnExpressionArgument
    ) -> Exists:
        relationship = getattr(self.model_class, relationship_name)
        related_model = relationship.property.mapper.class_
        alias = aliased(related_model)

        foreign_keys = list(relationship.property.local_remote_pairs)
        local_col, remote_col = foreign_keys[0]

        exists_clause = exists(alias).where(
            getattr(alias, remote_col.name) == getattr(self.model_class, local_col.name),
            self._adapt_condition(condition, alias),
        )
        return exists_clause

    def _adapt_condition(self, condition, alias):
        if isinstance(condition, BooleanClauseList):
            return condition.operator(
                *(self._adapt_condition(clause, alias) for clause in condition.clauses)
            )
        return condition.operator(getattr(alias, condition.left.key), condition.right.value)

    def apply_filter(self, query: Query, filter_expression: FilterExpression) -> Query:
        return query.filter(filter_expression.condition)

    def apply_joins(self, query: Query):
        for join_expr in self.joins:
            query = query.join(join_expr.target, join_expr.on, isouter=join_expr.is_outer)
        return query

    def apply_order_by(self, query: Query, order_by_expression: OrderByExpression) -> Query:
        fields = []
        for order_field in order_by_expression.fields:
            field = self.resolve_property(order_field.field_path)
            if order_field.direction == "-":
                field = field.desc()
            fields.append(field)
        return query.order_by(*fields)
