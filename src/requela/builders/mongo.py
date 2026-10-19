import dataclasses
import re
import types
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from functools import cache
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

try:
    from bson import Decimal128, ObjectId
    from bson.errors import InvalidId
except ImportError as e:  # pragma: no cover
    raise ImportError("MongoDB support requires pymongo>=4.13: pip install pymongo") from e

from requela.builders.base import QueryBuilder
from requela.dataclasses import FilterExpression, Operator, OrderByExpression

LOGICAL_OPERATORS = ("$and", "$or", "$nor")

OBJECT_ID_OPERATORS = {
    Operator.EQ,
    Operator.NE,
    Operator.GT,
    Operator.LT,
    Operator.GTE,
    Operator.LTE,
    Operator.IN,
    Operator.OUT,
}

SCALAR_TYPES = (str, int, float, bool, Decimal, datetime, date)


@dataclass
class MongoQuery:
    """A MongoDB `find` filter and sort, built from an RQL expression."""

    filter: dict[str, Any] = field(default_factory=dict)
    sort: list[tuple[str, int]] = field(default_factory=list)


@dataclass(frozen=True)
class ModelField:
    """A model attribute: its stored key, its (unwrapped) type and whether it is a list."""

    name: str
    key: str
    type: Any
    is_list: bool

    @property
    def is_model(self) -> bool:
        return is_model(self.type)


def is_model(annotation: Any) -> bool:
    """True for pydantic models (detected by `model_fields`) and dataclasses."""
    return isinstance(annotation, type) and (
        hasattr(annotation, "model_fields") or dataclasses.is_dataclass(annotation)
    )


def is_supported_scalar(annotation: Any) -> bool:
    return isinstance(annotation, type) and (
        annotation in SCALAR_TYPES or issubclass(annotation, Enum | ObjectId)
    )


def unwrap(annotation: Any) -> tuple[Any, bool]:
    """Strips `Annotated`, `X | None` and one list level; returns (type, is_list).

    Types that can't be reduced to a single type (e.g. `int | str`) come back unchanged and
    are rejected later as unsupported.
    """
    origin = get_origin(annotation)
    if origin is Annotated:
        return unwrap(get_args(annotation)[0])
    if origin in (Union, types.UnionType):
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        return unwrap(args[0]) if len(args) == 1 else (annotation, False)
    if origin in (list, Sequence):
        item_type, item_is_list = unwrap(get_args(annotation)[0])
        return (annotation, False) if item_is_list else (item_type, True)
    return annotation, False


@cache
def get_model_fields(model: type) -> dict[str, ModelField]:
    """The fields of a pydantic model or dataclass, by attribute name."""
    hints = get_type_hints(model, include_extras=True)
    if hasattr(model, "model_fields"):
        keys = {
            name: info.serialization_alias or info.alias or name
            for name, info in model.model_fields.items()
        }
    else:
        keys = {f.name: f.metadata.get("mongo_key", f.name) for f in dataclasses.fields(model)}

    model_fields = {}
    for name, key in keys.items():
        field_type, is_list = unwrap(hints[name])
        model_fields[name] = ModelField(name=name, key=key, type=field_type, is_list=is_list)
    return model_fields


class MongoQueryBuilder(QueryBuilder):
    """Builds a `MongoQuery` for a pydantic model or dataclass. It never runs the query."""

    def __init__(
        self,
        model_class: Any,
        resolve_alias_callback: Callable | None = None,
        validate_operator_and_field_callback: Callable | None = None,
        validate_ordering_callback: Callable | None = None,
        get_field_rule_callback: Callable | None = None,
    ):
        super().__init__(
            model_class,
            resolve_alias_callback=resolve_alias_callback,
            validate_operator_and_field_callback=validate_operator_and_field_callback,
            validate_ordering_callback=validate_ordering_callback,
            get_field_rule_callback=get_field_rule_callback,
        )
        # Stored key paths mapped to the field names used in the RQL expression, for errors
        self.field_names: dict[str, str] = {}

    def get_initial_query(self) -> MongoQuery:
        return MongoQuery()

    def get_field_type(self, field: str) -> type:
        model_field = self.resolve_path(field)[-1]
        if model_field.is_list or not is_supported_scalar(model_field.type):
            type_name = getattr(model_field.type, "__name__", repr(model_field.type))
            if model_field.is_list:
                type_name = f"list[{type_name}]"
            raise TypeError(f"Unsupported type for field '{field}': {type_name}.")
        return model_field.type

    def get_default_operators(self, field_type: type) -> set[Operator] | None:
        if issubclass(field_type, ObjectId):
            return OBJECT_ID_OPERATORS
        return super().get_default_operators(field_type)

    def resolve_path(self, path: str) -> list[ModelField]:
        """The model fields along a dotted attribute path, from the root model."""
        model_fields = []
        model: Any = self.model_class
        for part in path.split("."):
            fields = get_model_fields(model) if is_model(model) else {}
            if part not in fields:
                raise AttributeError(
                    f"Field '{path}' not found in model '{self.model_class.__name__}'."
                )
            model_fields.append(fields[part])
            model = fields[part].type
        return model_fields

    def resolve_key(self, prop: str) -> tuple[str, ModelField]:
        """The stored key path of a field in the RQL expression, and the field it ends at."""
        model_fields = self.resolve_path(self.resolve_alias(prop))
        key = ".".join(model_field.key for model_field in model_fields)
        self.field_names[key] = prop
        return key, model_fields[-1]

    def apply_and(self, *conditions: dict[str, Any]) -> dict[str, Any]:
        return {"$and": list(conditions)}

    def apply_or(self, *conditions: dict[str, Any]) -> dict[str, Any]:
        return {"$or": list(conditions)}

    def apply_not(self, condition: dict[str, Any]) -> dict[str, Any]:
        # $not only negates a single field's operator expression; $nor negates any condition
        return {"$nor": [condition]}

    def apply_eq(self, prop: str, value: Any) -> dict[str, Any]:
        key, value = self.prepare(prop, value, "eq")
        return {key: value}

    def apply_ne(self, prop: str, value: Any) -> dict[str, Any]:
        key, value = self.prepare(prop, value, "ne")
        return {key: {"$ne": value}}

    def apply_gt(self, prop: str, value: Any) -> dict[str, Any]:
        key, value = self.prepare(prop, value, "gt")
        return {key: {"$gt": value}}

    def apply_lt(self, prop: str, value: Any) -> dict[str, Any]:
        key, value = self.prepare(prop, value, "lt")
        return {key: {"$lt": value}}

    def apply_gte(self, prop: str, value: Any) -> dict[str, Any]:
        key, value = self.prepare(prop, value, "gte")
        return {key: {"$gte": value}}

    def apply_lte(self, prop: str, value: Any) -> dict[str, Any]:
        key, value = self.prepare(prop, value, "lte")
        return {key: {"$lte": value}}

    def apply_in(self, prop: str, value: Sequence[Any]) -> dict[str, Any]:
        key, values = self.prepare_items(prop, value)
        return {key: {"$in": values}}

    def apply_out(self, prop: str, value: Sequence[Any]) -> dict[str, Any]:
        key, values = self.prepare_items(prop, value)
        return {key: {"$nin": values}}

    def apply_like(self, prop: str, value: str) -> dict[str, Any]:
        key, _ = self.resolve_key(prop)
        return {key: {"$regex": self.to_regex(str(value))}}

    def apply_ilike(self, prop: str, value: str) -> dict[str, Any]:
        key, _ = self.resolve_key(prop)
        return {key: {"$regex": self.to_regex(str(value)), "$options": "i"}}

    def to_regex(self, pattern: str) -> str:
        # `*` matches anything; every other character, regex ones included, is literal.
        # `\z` anchors at the very end (`$` would also match before a trailing newline).
        return "^" + ".*".join(re.escape(part) for part in pattern.split("*")) + r"\z"

    def prepare(self, prop: str, value: Any, operator: str) -> tuple[str, Any]:
        key, model_field = self.resolve_key(prop)
        if model_field.is_model:
            if value is not None or operator not in ("eq", "ne"):
                raise ValueError(
                    f"`{operator}` can be applied to relationship only to test for null."
                )
            return key, None
        if value is None:
            return key, None
        return key, self.convert_value(prop, self.cast_value(model_field.type, value))

    def prepare_items(self, prop: str, values: Sequence[Any]) -> tuple[str, list[Any]]:
        key, model_field = self.resolve_key(prop)
        return key, [
            self.convert_value(prop, self.cast_value(model_field.type, value)) for value in values
        ]

    def cast_value(self, field_type: type, value: Any) -> Any:
        try:
            return self.cast(field_type, value)
        except (ValueError, TypeError, InvalidId) as e:
            raise ValueError(f"Cannot cast value {value!r} to {field_type.__name__}: {e}") from e

    def cast(self, field_type: type, value: Any) -> Any:
        if issubclass(field_type, Enum):
            return field_type(value).value
        if issubclass(field_type, ObjectId):
            return value if isinstance(value, ObjectId) else ObjectId(str(value))
        if field_type is bool:
            if isinstance(value, bool):
                return value
            raise TypeError("expected true or false")
        if field_type is int:
            return self.cast_int(value)
        if field_type is float:
            if isinstance(value, bool):
                raise TypeError("expected a number")
            return float(value)
        if field_type is Decimal:
            if isinstance(value, bool):
                raise TypeError("expected a number")
            return Decimal128(Decimal(str(value)))
        if field_type is datetime:
            return self.cast_datetime(value)
        if field_type is date:
            if isinstance(value, datetime):
                raise TypeError("expected a date without time")
            if isinstance(value, str):
                value = date.fromisoformat(value)
            # MongoDB has no date-only type: dates are stored as midnight UTC
            return datetime(value.year, value.month, value.day, tzinfo=UTC)
        return str(value)

    def cast_int(self, value: Any) -> int:
        if isinstance(value, bool):
            raise TypeError("expected an integer")
        if isinstance(value, int):
            return value
        number = float(value)
        if not number.is_integer():
            raise ValueError("expected an integer")
        return int(number)

    def cast_datetime(self, value: Any) -> datetime:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        elif not isinstance(value, datetime):
            # A date compares as midnight UTC, not as the whole day
            value = datetime(value.year, value.month, value.day)
        if value.tzinfo is None:
            # PyMongo stores and returns naive datetimes as UTC
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def apply_any(self, relationship_name: str, condition: dict[str, Any]) -> dict[str, Any]:
        model_fields = self.resolve_path(self.resolve_alias(relationship_name))
        relationship = model_fields[-1]
        if not (relationship.is_model and relationship.is_list):
            raise ValueError(
                f"any() requires a list of nested models: '{relationship_name}' is not one."
            )
        key = ".".join(model_field.key for model_field in model_fields)
        self.field_names[key] = relationship_name
        return {
            key: {
                "$elemMatch": self.relative_condition(
                    condition, key, relationship_name, relationship.type
                )
            }
        }

    def relative_condition(
        self, condition: dict[str, Any], key: str, relationship_name: str, model: type
    ) -> dict[str, Any]:
        """Rewrites the keys of a condition on `key.*` relative to `key`, for `$elemMatch`."""
        relative = {}
        for condition_key, value in condition.items():
            if condition_key in LOGICAL_OPERATORS:
                relative[condition_key] = [
                    self.relative_condition(item, key, relationship_name, model) for item in value
                ]
            elif condition_key.startswith(f"{key}."):
                relative_key = condition_key.removeprefix(f"{key}.")
                self.check_no_array_traversal(model, relative_key, condition_key)
                relative[relative_key] = value
            else:
                field_name = self.field_names.get(condition_key, condition_key)
                raise ValueError(
                    f"Field '{field_name}' is not part of relationship '{relationship_name}'."
                )
        return relative

    def check_condition(self, condition: dict[str, Any]) -> None:
        """Rejects fields reached through an array outside `any()`."""
        for key, value in condition.items():
            if key in LOGICAL_OPERATORS:
                for item in value:
                    self.check_condition(item)
            else:
                self.check_no_array_traversal(self.model_class, key, key)

    def check_no_array_traversal(self, model: type, key: str, full_key: str) -> None:
        # A key may end at an array ($elemMatch, null tests) but must not go through one
        parts = key.split(".")
        for part in parts[:-1]:
            model_field = next(f for f in get_model_fields(model).values() if f.key == part)
            if model_field.is_list:
                field_name = self.field_names.get(full_key, full_key)
                raise ValueError(
                    f"Field '{field_name}' goes through the list '{model_field.name}': "
                    "use any() to filter on it."
                )
            model = model_field.type

    def apply_filter(self, query: MongoQuery, filter_expression: FilterExpression) -> MongoQuery:
        condition = filter_expression.condition
        self.check_condition(condition)
        query.filter = {"$and": [query.filter, condition]} if query.filter else condition
        return query

    def apply_joins(self, query: MongoQuery) -> MongoQuery:
        return query

    def apply_order_by(
        self, query: MongoQuery, order_by_expression: OrderByExpression
    ) -> MongoQuery:
        for order_field in order_by_expression.fields:
            model_fields = self.resolve_path(self.resolve_alias(order_field.field_path))
            if any(model_field.is_list for model_field in model_fields):
                raise ValueError(
                    f"Order by '{order_field.field_path}' is not possible: it is a list "
                    "or inside a list."
                )
            if model_fields[-1].is_model:
                raise ValueError(
                    f"Order by '{order_field.field_path}' is not possible: it is a nested model."
                )
            key = ".".join(model_field.key for model_field in model_fields)
            query.sort.append((key, -1 if order_field.direction == "-" else 1))
        return query

    def build_query(self, rql_query: str, initial_query: MongoQuery | None = None) -> MongoQuery:
        self.field_names = {}
        # Never modify the caller's query
        query = (
            MongoQuery(filter=dict(initial_query.filter), sort=list(initial_query.sort))
            if initial_query is not None
            else None
        )
        return super().build_query(rql_query=rql_query, initial_query=query)
