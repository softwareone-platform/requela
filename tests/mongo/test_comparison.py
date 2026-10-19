from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from bson import Decimal128, ObjectId

from requela.builders.mongo import MongoQueryBuilder
from tests.mongo.models import Event, Item

OBJECT_ID = "65f0c0ffee0ddba11ad0beef"


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("eq(evt_class,quota)", {"evt_class": "quota"}),
        ("eq(evt_class,'quoted value')", {"evt_class": "quoted value"}),
        ("eq(evt_class,123)", {"evt_class": "123"}),
        ("eq(evt_class,empty())", {"evt_class": ""}),
        ("eq(note,null())", {"note": None}),
        ("eq(count,3)", {"count": 3}),
        ("eq(count,3.0)", {"count": 3}),
        ("eq(cost,3)", {"cost": 3.0}),
        ("eq(ack,true)", {"ack": True}),
        ("eq(level,ERROR)", {"level": "ERROR"}),
        ("eq(severity,2)", {"severity": 2}),
        (f"eq(id,'{OBJECT_ID}')", {"_id": ObjectId(OBJECT_ID)}),
        ("eq(source,null())", {"source": None}),
        ("eq(source.name,aws)", {"source.name": "aws"}),
    ],
)
def test_eq_builds_an_equality_filter(query_string: str, expected: dict[str, Any]) -> None:
    """`eq` matches the value cast to the field type, on the stored key."""
    assert MongoQueryBuilder(Event).build_query(query_string).filter == expected


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("ne(evt_class,quota)", {"evt_class": {"$ne": "quota"}}),
        ("ne(note,null())", {"note": {"$ne": None}}),
        ("ne(source,null())", {"source": {"$ne": None}}),
    ],
)
def test_ne_builds_a_not_equal_filter(query_string: str, expected: dict[str, Any]) -> None:
    """`ne` uses `$ne`, which also matches documents where the field is null or missing."""
    assert MongoQueryBuilder(Event).build_query(query_string).filter == expected


@pytest.mark.parametrize(
    ("operator", "mongo_operator"),
    [("gt", "$gt"), ("gte", "$gte"), ("lt", "$lt"), ("lte", "$lte")],
)
def test_range_operators_map_to_mongo_operators(operator: str, mongo_operator: str) -> None:
    """`gt`, `gte`, `lt` and `lte` map to the MongoDB operator of the same name."""
    query = MongoQueryBuilder(Event).build_query(f"{operator}(count,5)")
    assert query.filter == {"count": {mongo_operator: 5}}


def test_in_casts_each_item() -> None:
    """`in` uses `$in` with every item cast to the field type."""
    query = MongoQueryBuilder(Event).build_query("in(count,(1,2.0,3))")
    assert query.filter == {"count": {"$in": [1, 2, 3]}}


def test_out_casts_each_item() -> None:
    """`out` uses `$nin` with every item cast to the field type."""
    query = MongoQueryBuilder(Event).build_query("out(level,(INFO,ERROR))")
    assert query.filter == {"level": {"$nin": ["INFO", "ERROR"]}}


@pytest.mark.parametrize(
    ("pattern", "regex"),
    [
        ("quota", "^quota\\z"),
        ("quota*", "^quota.*\\z"),
        ("*quota", "^.*quota\\z"),
        ("*quota*", "^.*quota.*\\z"),
        ("a*b", "^a.*b\\z"),
        ("a.b*", "^a\\.b.*\\z"),
        ("(x)+[y]?", "^\\(x\\)\\+\\[y\\]\\?\\z"),
    ],
)
def test_like_builds_an_anchored_regex(pattern: str, regex: str) -> None:
    """`like` turns `*` into `.*` and matches every other character literally."""
    query = MongoQueryBuilder(Event).build_query(f"like(description,'{pattern}')")
    assert query.filter == {"description": {"$regex": regex}}


def test_ilike_builds_a_case_insensitive_regex() -> None:
    """`ilike` builds the same regex as `like`, with the case-insensitive option."""
    query = MongoQueryBuilder(Event).build_query("ilike(description,*Quota*)")
    assert query.filter == {"description": {"$regex": "^.*Quota.*\\z", "$options": "i"}}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2024-01-01", datetime(2024, 1, 1, tzinfo=UTC)),
        ("2024-01-01T10:30:00+00:00", datetime(2024, 1, 1, 10, 30, tzinfo=UTC)),
        ("2024-01-01T12:30:00+02:00", datetime(2024, 1, 1, 10, 30, tzinfo=UTC)),
        ("'2024-01-01T10:30:00'", datetime(2024, 1, 1, 10, 30, tzinfo=UTC)),
    ],
)
def test_datetime_values_are_converted_to_utc(value: str, expected: datetime) -> None:
    """Dates become midnight UTC, naive datetimes are taken as UTC, others converted."""
    query = MongoQueryBuilder(Event).build_query(f"gte(time,{value})")
    assert query.filter == {"time": {"$gte": expected}}
    assert query.filter["time"]["$gte"].utcoffset() == timedelta(0)


@pytest.mark.parametrize("value", ["2024-01-02", "'2024-01-02'"])
def test_date_values_are_stored_as_midnight_utc(value: str) -> None:
    """A `date` field compares as a datetime at midnight UTC."""
    query = MongoQueryBuilder(Event).build_query(f"eq(day,{value})")
    assert query.filter == {"day": datetime(2024, 1, 2, tzinfo=UTC)}


def test_decimal_values_become_decimal128() -> None:
    """A `Decimal` field compares as `Decimal128`, the type PyMongo stores."""
    query = MongoQueryBuilder(Item).build_query("eq(price,'10.50')")
    assert query.filter == {"price": Decimal128(Decimal("10.50"))}


def test_dataclass_fields_use_the_mongo_key_metadata() -> None:
    """A dataclass field with `mongo_key` metadata is filtered on that key."""
    query = MongoQueryBuilder(Item).build_query(f"eq(id,'{OBJECT_ID}')")
    assert query.filter == {"_id": ObjectId(OBJECT_ID)}


@pytest.mark.parametrize(
    ("query_string", "message"),
    [
        ("eq(count,3.5)", "Cannot cast value 3.5 to int: expected an integer"),
        ("eq(count,abc)", "Cannot cast value 'abc' to int"),
        ("eq(count,true)", "Cannot cast value True to int: expected an integer"),
        ("eq(cost,true)", "Cannot cast value True to float: expected a number"),
        ("eq(ack,yes)", "Cannot cast value 'yes' to bool: expected true or false"),
        ("eq(level,FATAL)", "Cannot cast value 'FATAL' to Level"),
        ("eq(id,nothex)", "Cannot cast value 'nothex' to ObjectId"),
        ("eq(time,yesterday)", "Cannot cast value 'yesterday' to datetime"),
        (
            "eq(day,2024-01-02T10:00:00+00:00)",
            "Cannot cast value .* to date: expected a date without time",
        ),
    ],
)
def test_values_that_cannot_be_cast_are_rejected(query_string: str, message: str) -> None:
    """A value that doesn't fit the field type raises `ValueError` instead of matching nothing."""
    with pytest.raises(ValueError, match=message):
        MongoQueryBuilder(Event).build_query(query_string)


def test_decimal_rejects_booleans() -> None:
    """A boolean is not accepted as a `Decimal` value."""
    with pytest.raises(ValueError, match="Cannot cast value True to Decimal: expected a number"):
        MongoQueryBuilder(Item).build_query("eq(price,true)")


@pytest.mark.parametrize(
    "query_string",
    ["eq(source,aws)", "gt(source,null())", "ne(source,aws)"],
)
def test_nested_model_can_only_be_tested_for_null(query_string: str) -> None:
    """A nested model field accepts only `eq`/`ne` with `null()`, as SQLAlchemy relationships."""
    with pytest.raises(ValueError, match="can be applied to relationship only to test for null"):
        MongoQueryBuilder(Event).build_query(query_string)


def test_unknown_field_is_rejected() -> None:
    """A field that is not on the model raises `AttributeError`."""
    with pytest.raises(AttributeError, match="Field 'missing' not found in model 'Event'"):
        MongoQueryBuilder(Event).build_query("eq(missing,1)")


def test_path_into_a_non_model_field_is_rejected() -> None:
    """A dotted path into a field that is not a nested model is reported as unknown."""
    with pytest.raises(AttributeError, match="Field 'payload.key' not found in model 'Event'"):
        MongoQueryBuilder(Event).build_query("eq(payload.key,1)")


def test_aware_datetime_values_keep_their_instant() -> None:
    """An aware datetime value keeps the same instant once converted to UTC."""
    offset = timezone(timedelta(hours=-5))
    query = MongoQueryBuilder(Event).build_query("lt(time,2024-01-01T19:00:00-05:00)")
    assert query.filter["time"]["$lt"] == datetime(2024, 1, 1, 19, tzinfo=offset)
