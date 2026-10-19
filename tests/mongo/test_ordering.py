import pytest

from requela.builders.mongo import MongoQueryBuilder
from tests.mongo.models import Event


def test_order_by_builds_sort_on_stored_keys() -> None:
    """`order_by` sorts ascending by default and descending with `-`, on stored keys."""
    query = MongoQueryBuilder(Event).build_query("order_by(-time,id,+source.name)")
    assert query.sort == [("time", -1), ("_id", 1), ("source.name", 1)]


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("tags", "it is a list or inside a list"),
        ("tags.name", "it is a list or inside a list"),
        ("labels", "it is a list or inside a list"),
        ("source", "it is a nested model"),
    ],
)
def test_order_by_rejects_lists_and_nested_models(field: str, reason: str) -> None:
    """Ordering on a list, a field inside a list or a nested model is rejected."""
    with pytest.raises(ValueError, match=f"Order by '{field}' is not possible: {reason}"):
        MongoQueryBuilder(Event).build_query(f"order_by({field})")
