import pytest

from requela.builders.mongo import MongoQueryBuilder
from tests.mongo.models import Event


def test_any_matches_one_element_with_elem_match() -> None:
    """`any()` uses `$elemMatch` with field names relative to the list."""
    query = MongoQueryBuilder(Event).build_query("any(tags,eq(tags.name,env))")
    assert query.filter == {"tags": {"$elemMatch": {"name": "env"}}}


def test_any_applies_all_conditions_to_the_same_element() -> None:
    """All the conditions inside `any()` end up in one `$elemMatch`."""
    query = MongoQueryBuilder(Event).build_query(
        "any(tags,and(eq(tags.name,env),or(eq(tags.value,prod),not(eq(tags.value,dev)))))"
    )
    assert query.filter == {
        "tags": {
            "$elemMatch": {
                "$and": [
                    {"name": "env"},
                    {"$or": [{"value": "prod"}, {"$nor": [{"value": "dev"}]}]},
                ]
            }
        }
    }


def test_any_combines_with_logical_operators() -> None:
    """`any()` can be used inside `or` and `not` like any other condition."""
    query = MongoQueryBuilder(Event).build_query(
        "or(eq(level,ERROR),not(any(tags,eq(tags.name,env))))"
    )
    assert query.filter == {
        "$or": [{"level": "ERROR"}, {"$nor": [{"tags": {"$elemMatch": {"name": "env"}}}]}]
    }


def test_nested_any_matches_lists_inside_lists() -> None:
    """`any()` inside `any()` matches a list nested in the elements of another list."""
    query = MongoQueryBuilder(Event).build_query(
        "any(tags,and(eq(tags.name,env),any(tags.aliases,eq(tags.aliases.name,environment))))"
    )
    assert query.filter == {
        "tags": {
            "$elemMatch": {
                "$and": [
                    {"name": "env"},
                    {"aliases": {"$elemMatch": {"name": "environment"}}},
                ]
            }
        }
    }


@pytest.mark.parametrize(
    ("query_string", "field_name", "list_name"),
    [
        ("eq(tags.name,env)", "tags.name", "tags"),
        ("or(eq(level,ERROR),eq(tags.name,env))", "tags.name", "tags"),
        ("any(tags.aliases,eq(tags.aliases.name,x))", "tags.aliases", "tags"),
        ("any(tags,eq(tags.aliases.name,x))", "tags.aliases.name", "aliases"),
    ],
)
def test_field_inside_a_list_requires_any(
    query_string: str, field_name: str, list_name: str
) -> None:
    """A field reached through a list outside `any()` on that list is rejected."""
    with pytest.raises(
        ValueError,
        match=f"Field '{field_name}' goes through the list '{list_name}': use any\\(\\)",
    ):
        MongoQueryBuilder(Event).build_query(query_string)


def test_any_rejects_field_outside_the_relationship() -> None:
    """A field inside `any()` that is not reached through the list is rejected."""
    with pytest.raises(ValueError, match="Field 'level' is not part of relationship 'tags'"):
        MongoQueryBuilder(Event).build_query("any(tags,eq(level,ERROR))")


@pytest.mark.parametrize("relationship", ["source", "level", "labels"])
def test_any_requires_a_list_of_nested_models(relationship: str) -> None:
    """`any()` on a field that is not a list of nested models is rejected."""
    with pytest.raises(ValueError, match="any\\(\\) requires a list of nested models: "):
        MongoQueryBuilder(Event).build_query(f"any({relationship},eq({relationship},null()))")
