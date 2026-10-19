from datetime import UTC, datetime

import pytest
from bson import ObjectId

from requela.builders.mongo import MongoQueryBuilder
from requela.exceptions import RequelaError
from requela.rules import FieldRule
from tests.mongo.models import CamelEvent
from tests.mongo.rules import (
    EventRules,
    EventWithConvertersRules,
    EventWithUnsupportedFieldsRules,
    ItemRules,
    KeeperEventRules,
    MongoRules,
)

OBJECT_ID = "65f0c0ffee0ddba11ad0beef"


def test_rules_use_the_builder_set_on_the_abstract_base() -> None:
    """A rules class inherits `__builder__` from its abstract base."""
    assert isinstance(EventRules().builder, MongoQueryBuilder)


def test_abstract_rules_class_cannot_be_instantiated() -> None:
    """An abstract rules class only shares settings and raises `TypeError` if instantiated."""
    with pytest.raises(TypeError, match="MongoRules is abstract and cannot be instantiated"):
        MongoRules()


def test_subclass_of_abstract_rules_must_define_model() -> None:
    """A subclass of an abstract rules class is concrete again and must define `__model__`."""
    with pytest.raises(TypeError, match="NoModelRules must define __model__"):
        type("NoModelRules", (MongoRules,), {"name": FieldRule()})


def test_dataclass_model_is_validated() -> None:
    """Rules on a dataclass model infer the operators of each field from its type."""
    rules = ItemRules()
    assert rules.build_query(f"in(id,('{OBJECT_ID}'))").filter == {
        "_id": {"$in": [ObjectId(OBJECT_ID)]}
    }


def test_unsupported_field_types_fail_when_rules_are_created() -> None:
    """Rules on fields that can't be filtered fail when created, with one error per field."""
    with pytest.raises(ExceptionGroup) as exc_info:
        EventWithUnsupportedFieldsRules()

    assert sorted(str(error) for error in exc_info.value.exceptions) == [
        "Field 'payload_key' not found in model 'Event'.",
        "Unsupported type for field 'code': int | str.",
        "Unsupported type for field 'extra': Any.",
        "Unsupported type for field 'labels': list[str].",
        "Unsupported type for field 'payload': dict.",
        "Unsupported type for field 'reference': UUID.",
    ]


def test_rules_resolve_aliases_and_sources_to_stored_keys() -> None:
    """Field and relationship aliases and `source` are resolved to the stored keys."""
    query = EventRules().build_query(
        "and(eq(type,quota),eq(origin.name,aws),any(tags,eq(tags.key,env)))"
    )
    assert query.filter == {
        "$and": [
            {"evt_class": "quota"},
            {"source.name": "aws"},
            {"tags": {"$elemMatch": {"name": "env"}}},
        ]
    }


def test_pydantic_aliases_map_to_stored_keys() -> None:
    """The serialization alias, then the alias, of a pydantic field is its stored key."""
    query = MongoQueryBuilder(CamelEvent).build_query("and(eq(event_class,a),eq(created_by,b))")
    assert query.filter == {"$and": [{"eventClass": "a"}, {"author": "b"}]}


@pytest.mark.parametrize(
    ("query_string", "message"),
    [
        ("ne(description,x)", "Operator 'ne' is not allowed for field 'description'."),
        ("order_by(ack)", "Order by 'ack' is not allowed."),
        ("eq(evt_class,x)", "Relation with alias 'evt_class' not found"),
        ("eq(tags.missing,x)", "Relation with alias 'missing' not found"),
        ("eq(count,1.5)", "Cannot cast value 1.5 to int: expected an integer"),
    ],
)
def test_invalid_queries_raise_requela_error(query_string: str, message: str) -> None:
    """Rejected operators, orderings, unknown fields and bad values raise `RequelaError`."""
    with pytest.raises(RequelaError, match=message):
        EventRules().build_query(query_string)


def test_value_converter_converts_values_after_casting() -> None:
    """`value_converter` receives the value cast to the field type and its result is used."""
    query = KeeperEventRules().build_query("gte(time,2024-01-01)")
    assert query.filter == {"time": {"$gte": int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())}}


def test_value_converter_converts_each_item_of_in() -> None:
    """`value_converter` is applied to every item of `in` and `out`."""
    query = EventWithConvertersRules().build_query("in(count,(1,2))")
    assert query.filter == {"count": {"$in": ["1", "2"]}}


def test_value_converter_is_not_applied_to_null() -> None:
    """`null()` is never passed to `value_converter`."""
    query = EventWithConvertersRules().build_query("eq(note,null())")
    assert query.filter == {"note": None}


def test_value_converter_is_not_applied_to_like_patterns() -> None:
    """`like`/`ilike` patterns are wildcard strings and are never converted."""
    query = EventWithConvertersRules().build_query("and(eq(description,abc),like(description,ab*))")
    assert query.filter == {
        "$and": [{"description": "ABC"}, {"description": {"$regex": "^ab.*\\z"}}]
    }


def test_value_converter_errors_raise_requela_error() -> None:
    """A `ValueError` from `value_converter` is raised as `RequelaError`."""
    with pytest.raises(RequelaError, match="Rejected value 'x'"):
        EventWithConvertersRules().build_query("eq(note,x)")


def test_documentation_lists_object_id_fields_and_relationships() -> None:
    """`get_documentation()` lists `ObjectId` fields and nested relationships with aliases."""
    documentation = EventRules().get_documentation().splitlines()
    assert "|id|eq, gt, gte, in, lt, lte, ne, out|yes|" in documentation
    assert "|origin|eq, ne|no|" in documentation
    assert "|origin.name|eq, ilike, in, like, ne, out|yes|" in documentation
    assert "|tags.aliases.name|eq, ilike, in, like, ne, out|yes|" in documentation
    assert "|tags.key|eq, ilike, in, like, ne, out|yes|" in documentation
