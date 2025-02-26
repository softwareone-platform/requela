import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from requela.dataclasses import FilterExpression, Operators, OrderByExpression
from requela.parser import parse
from requela.transformer import RQLTransformer

logger = logging.getLogger(__name__)


class QueryBuilder(ABC):
    def __init__(self):
        self.transformer = RQLTransformer(
            Operators(
                and_op=self.apply_and,
                or_op=self.apply_or,
                not_op=self.apply_not,
                eq_op=self.apply_eq,
                ne_op=self.apply_ne,
                gt_op=self.apply_gt,
                lt_op=self.apply_lt,
                gte_op=self.apply_gte,
                lte_op=self.apply_lte,
                in_op=self.apply_in,
                out_op=self.apply_out,
                like_op=self.apply_like,
                ilike_op=self.apply_ilike,
                any_op=self.apply_any,
            )
        )

    @abstractmethod
    def get_initial_query(self):
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

    def build_query(self, rql_query: str, initial_query: Any = None) -> Any:
        query = initial_query or self.get_initial_query()
        ast = parse(rql_query)
        expressions = self.transformer.transform(ast)
        for expression in expressions:
            if isinstance(expression, FilterExpression):
                query = self.apply_filter(query, expression)
            if isinstance(expression, OrderByExpression):
                query = self.apply_order_by(query, expression)
        return self.apply_joins(query)
