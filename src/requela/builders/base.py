import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from datetime import date, datetime
from functools import partial
from typing import Any

from lark.exceptions import VisitError

from requela.dataclasses import FilterExpression, Operator, OperatorFunctions, OrderByExpression
from requela.parser import parse
from requela.transformer import RQLTransformer

logger = logging.getLogger(__name__)


class QueryBuilder(ABC):
    def __init__(
        self,
        model_class: Any,
        resolve_alias_callback: Callable | None = None,
        validate_operator_and_field_callback: Callable | None = None,
        validate_ordering_callback: Callable | None = None,
    ):
        self.model_class = model_class
        self.resolve_alias_callback = resolve_alias_callback
        self.validate_operator_and_field_callback = validate_operator_and_field_callback
        self.validate_ordering_callback = validate_ordering_callback
        self.transformer = RQLTransformer(
            OperatorFunctions(
                and_op=self.apply_and,
                or_op=self.apply_or,
                not_op=self.apply_not,
                eq_op=partial(self.apply_operator, Operator.EQ),
                ne_op=partial(self.apply_operator, Operator.NE),
                gt_op=partial(self.apply_operator, Operator.GT),
                lt_op=partial(self.apply_operator, Operator.LT),
                gte_op=partial(self.apply_operator, Operator.GTE),
                lte_op=partial(self.apply_operator, Operator.LTE),
                in_op=partial(self.apply_operator, Operator.IN),
                out_op=partial(self.apply_operator, Operator.OUT),
                like_op=partial(self.apply_operator, Operator.LIKE),
                ilike_op=partial(self.apply_operator, Operator.ILIKE),
                any_op=self.apply_any,
            )
        )

    @abstractmethod
    def get_initial_query(self):
        pass

    @abstractmethod
    def get_field_type(self, field: str) -> type:
        pass

    @abstractmethod
    def apply_and(self, *conditions):
        pass

    @abstractmethod
    def apply_or(self, *conditions):
        pass

    @abstractmethod
    def apply_not(self, condition):
        pass

    @abstractmethod
    def apply_eq(self, prop: str, value: str | date | datetime | int | float | None):
        pass

    @abstractmethod
    def apply_ne(self, prop: str, value: str | date | datetime | int | float | None):
        pass

    @abstractmethod
    def apply_gt(self, prop: str, value: date | datetime | int | float):
        pass

    @abstractmethod
    def apply_lt(self, prop: str, value: date | datetime | int | float):
        pass

    @abstractmethod
    def apply_gte(self, prop: str, value: date | datetime | int | float):
        pass

    @abstractmethod
    def apply_lte(self, prop: str, value: date | datetime | int | float):
        pass

    @abstractmethod
    def apply_in(self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]):
        pass

    @abstractmethod
    def apply_out(self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]):
        pass

    @abstractmethod
    def apply_like(self, prop: str, value: str):
        pass

    @abstractmethod
    def apply_ilike(self, prop: str, value: str):
        pass

    @abstractmethod
    def apply_any(self, prop: str, condition: Any) -> Any:
        pass

    @abstractmethod
    def apply_joins(self, query):
        pass

    @abstractmethod
    def apply_order_by(self, query: Any, order_by_expression: OrderByExpression) -> Any:
        pass

    @abstractmethod
    def apply_filter(self, query, filter_expression: FilterExpression) -> Any:
        pass

    def apply_operator(self, operator: Operator, prop: str, value: Any):
        self.validate_operator_and_field(prop, operator)
        return getattr(self, f"apply_{operator.value}")(prop, value)

    def validate_operator_and_field(self, field: str, operator: Operator) -> None:
        if self.validate_operator_and_field_callback:
            return self.validate_operator_and_field_callback(field, operator)

    def resolve_alias(self, alias: str) -> str:
        if self.resolve_alias_callback:
            return self.resolve_alias_callback(alias)
        return alias

    def build_query(self, rql_query: str, initial_query: Any = None) -> Any:
        query = initial_query if initial_query is not None else self.get_initial_query()
        ast = parse(rql_query)
        try:
            expressions = self.transformer.transform(ast)
        except VisitError as e:
            raise e.orig_exc
        for expression in expressions:
            if isinstance(expression, FilterExpression):
                query = self.apply_filter(query, expression)
            if isinstance(expression, OrderByExpression):
                if self.validate_ordering_callback:
                    for field in expression.fields:
                        self.validate_ordering_callback(field.field_path)
                query = self.apply_order_by(query, expression)
        return self.apply_joins(query)
