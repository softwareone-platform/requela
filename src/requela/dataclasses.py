from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class FilterExpression:
    condition: Any


@dataclass
class OrderField:
    direction: str
    field_path: str


@dataclass
class JoinExpression:
    target: Any
    on: Any


@dataclass
class OrderByExpression:
    fields: list[OrderField]


@dataclass
class Operators:
    # logical
    and_op: Callable
    or_op: Callable
    not_op: Callable

    # comparison
    eq_op: Callable
    ne_op: Callable
    gt_op: Callable
    lt_op: Callable
    gte_op: Callable
    lte_op: Callable
    in_op: Callable
    out_op: Callable
    like_op: Callable
    ilike_op: Callable

    # any operator
    any_op: Callable
