from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from bson import ObjectId

from tests.integration.mongo.conftest import FindDocuments
from tests.mongo.models import KeeperEvent
from tests.mongo.rules import EventRules, ItemRules, KeeperEventRules

ALL_EVENTS = {"disk full", "quota exceeded", "Quota reset", "a.b literal"}


@pytest.mark.usefixtures("sample_events")
@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("eq(level,ERROR)", {"disk full"}),
        ("ne(level,INFO)", {"disk full", "quota exceeded"}),
        ("gt(count,1)", {"disk full", "quota exceeded"}),
        ("lte(count,1)", {"Quota reset", "a.b literal"}),
        ("in(level,(INFO,WARNING))", {"quota exceeded", "Quota reset", "a.b literal"}),
        ("out(level,(INFO,WARNING))", {"disk full"}),
        ("eq(ack,true)", {"quota exceeded", "a.b literal"}),
        ("gt(time,2024-01-02)", {"disk full", "a.b literal"}),
        ("lt(time,2024-01-02T00:00:00+01:00)", {"Quota reset"}),
        ("eq(type,quota)", ALL_EVENTS),
        ("and(eq(level,INFO),eq(ack,true))", {"a.b literal"}),
        ("or(eq(level,ERROR),eq(level,WARNING))", {"disk full", "quota exceeded"}),
        ("not(eq(level,INFO))", {"disk full", "quota exceeded"}),
        ("eq(origin.name,aws)", {"disk full"}),
    ],
)
async def test_operators_select_the_matching_documents(
    find_documents: FindDocuments, query_string: str, expected: set[str]
) -> None:
    """Each RQL operator selects the expected documents on a real MongoDB."""
    query = EventRules().build_query(query_string)

    documents = await find_documents("events", query)

    assert {document["description"] for document in documents} == expected


@pytest.mark.usefixtures("sample_events")
@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("like(description,quota*)", {"quota exceeded"}),
        ("ilike(description,quota*)", {"quota exceeded", "Quota reset"}),
        ("like(description,*full)", {"disk full"}),
        ("like(description,*s*f*)", {"disk full"}),
        ("like(description,a.b*)", {"a.b literal"}),
        ("like(description,a?b*)", set()),
        ("like(description,disk)", set()),
    ],
)
async def test_like_matches_wildcards_and_literal_characters(
    find_documents: FindDocuments, query_string: str, expected: set[str]
) -> None:
    """`*` matches any characters; every other character, regex ones included, is literal."""
    query = EventRules().build_query(query_string)

    documents = await find_documents("events", query)

    assert {document["description"] for document in documents} == expected


@pytest.mark.usefixtures("sample_events")
@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("eq(note,null())", {"quota exceeded", "Quota reset"}),
        ("ne(note,null())", {"disk full", "a.b literal"}),
        ("ne(note,check)", {"quota exceeded", "Quota reset", "a.b literal"}),
        ("out(note,(check,x))", {"quota exceeded", "Quota reset"}),
        ("not(eq(note,check))", {"quota exceeded", "Quota reset", "a.b literal"}),
        ("eq(origin,null())", {"Quota reset", "a.b literal"}),
    ],
)
async def test_null_also_matches_missing_fields(
    find_documents: FindDocuments, query_string: str, expected: set[str]
) -> None:
    """`null()` matches null and missing fields; `ne`, `out` and `not` include them."""
    query = EventRules().build_query(query_string)

    documents = await find_documents("events", query)

    assert {document["description"] for document in documents} == expected


@pytest.mark.usefixtures("sample_events")
@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("any(tags,eq(tags.key,env))", {"disk full", "quota exceeded", "a.b literal"}),
        ("any(tags,and(eq(tags.key,team),eq(tags.value,dev)))", {"a.b literal"}),
        (
            "and(any(tags,eq(tags.key,team)),any(tags,eq(tags.value,dev)))",
            {"quota exceeded", "a.b literal"},
        ),
        ("not(any(tags,eq(tags.key,env)))", {"Quota reset"}),
        (
            "or(eq(level,INFO),any(tags,eq(tags.value,dev)))",
            {"quota exceeded", "Quota reset", "a.b literal"},
        ),
        (
            "any(tags,and(any(tags.aliases,eq(tags.aliases.name,operations))))",
            {"disk full"},
        ),
    ],
)
async def test_any_matches_elements_of_nested_lists(
    find_documents: FindDocuments, query_string: str, expected: set[str]
) -> None:
    """`any()` needs one element to match all its conditions; separate `any()` are independent."""
    query = EventRules().build_query(query_string)

    documents = await find_documents("events", query)

    assert {document["description"] for document in documents} == expected


@pytest.mark.usefixtures("sample_events")
@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("order_by(-time)", ["a.b literal", "disk full", "quota exceeded", "Quota reset"]),
        (
            "order_by(count,description)",
            ["Quota reset", "a.b literal", "quota exceeded", "disk full"],
        ),
        (
            "order_by(note,description)",
            ["Quota reset", "quota exceeded", "disk full", "a.b literal"],
        ),
    ],
)
async def test_order_by_sorts_documents(
    find_documents: FindDocuments, query_string: str, expected: list[str]
) -> None:
    """`order_by` sorts the documents; null and missing values come first."""
    query = EventRules().build_query(query_string)

    documents = await find_documents("events", query)

    assert [document["description"] for document in documents] == expected


async def test_object_id_filter_selects_the_document(
    find_documents: FindDocuments, event_factory: Callable[..., ObjectId]
) -> None:
    """An `id` given as a hex string selects the document with that `ObjectId`."""
    event_id = event_factory(description="target")
    event_factory(description="other")
    query = EventRules().build_query(f"eq(id,'{event_id}')")

    documents = await find_documents("events", query)

    assert [document["_id"] for document in documents] == [event_id]


async def test_value_converter_filters_on_the_stored_format(
    find_documents: FindDocuments, keeper_event_factory: Callable[[datetime], ObjectId]
) -> None:
    """A datetime filter on a timestamp stored as int selects through `value_converter`."""
    keeper_event_factory(datetime(2024, 1, 1, tzinfo=UTC))
    later_id = keeper_event_factory(datetime(2024, 1, 3, tzinfo=UTC))
    query = KeeperEventRules().build_query("gt(time,2024-01-02)")

    documents = await find_documents("keeper_events", query)

    assert [document["_id"] for document in documents] == [later_id]


async def test_model_reads_a_timestamp_stored_as_int(
    find_documents: FindDocuments, keeper_event_factory: Callable[[datetime], ObjectId]
) -> None:
    """The pydantic model parses the int timestamp stored by keeper into a datetime."""
    keeper_event_factory(datetime(2024, 1, 3, tzinfo=UTC))

    documents = await find_documents(
        "keeper_events", KeeperEventRules().build_query("order_by(id)")
    )

    assert KeeperEvent.model_validate(documents[0]).time == datetime(2024, 1, 3, tzinfo=UTC)


async def test_decimal_and_date_filters_select_dataclass_documents(
    find_documents: FindDocuments, item_factory: Callable[..., ObjectId]
) -> None:
    """`Decimal` and `date` values compare with the `Decimal128` and datetime stored."""
    item_factory(name="cheap", price=Decimal("9.99"), created=datetime(2024, 1, 1))
    item_factory(name="dear", price=Decimal("10.50"), created=datetime(2024, 1, 2))
    query = ItemRules().build_query("and(gte(price,'10.00'),eq(created,2024-01-02))")

    documents = await find_documents("items", query)

    assert [document["name"] for document in documents] == ["dear"]
