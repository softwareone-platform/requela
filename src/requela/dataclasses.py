from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
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
    is_outer: bool = False


@dataclass
class OrderByExpression:
    fields: list[OrderField]


class Operator(Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    OUT = "out"
    LIKE = "like"
    ILIKE = "ilike"
    ANY = "any"


# Default operator sets based on field types
DEFAULT_OPERATORS = {
    str: {
        Operator.EQ,
        Operator.NE,
        Operator.IN,
        Operator.OUT,
        Operator.LIKE,
        Operator.ILIKE,
    },
    int: {
        Operator.EQ,
        Operator.NE,
        Operator.GT,
        Operator.LT,
        Operator.GTE,
        Operator.LTE,
        Operator.IN,
        Operator.OUT,
    },
    float: {
        Operator.EQ,
        Operator.NE,
        Operator.GT,
        Operator.LT,
        Operator.GTE,
        Operator.LTE,
        Operator.IN,
        Operator.OUT,
    },
    bool: {Operator.EQ, Operator.NE},
    datetime: {
        Operator.EQ,
        Operator.NE,
        Operator.GT,
        Operator.LT,
        Operator.GTE,
        Operator.LTE,
    },
    date: {
        Operator.EQ,
        Operator.NE,
        Operator.GT,
        Operator.LT,
        Operator.GTE,
        Operator.LTE,
    },
    Enum: {Operator.EQ, Operator.NE, Operator.IN, Operator.OUT},
}


@dataclass
class OperatorFunctions:
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
