from requela.builders.mongo import MongoQuery, MongoQueryBuilder
from tests.mongo.models import Event


def test_and_combines_conditions_with_and() -> None:
    """`and` puts its conditions in an `$and` list."""
    query = MongoQueryBuilder(Event).build_query("and(eq(level,ERROR),gt(count,1))")
    assert query.filter == {"$and": [{"level": "ERROR"}, {"count": {"$gt": 1}}]}


def test_or_combines_conditions_with_or() -> None:
    """`or` puts its conditions in an `$or` list."""
    query = MongoQueryBuilder(Event).build_query("or(eq(level,ERROR),gt(count,1))")
    assert query.filter == {"$or": [{"level": "ERROR"}, {"count": {"$gt": 1}}]}


def test_not_negates_any_condition_with_nor() -> None:
    """`not` uses `$nor`, which, unlike `$not`, negates any condition."""
    query = MongoQueryBuilder(Event).build_query("not(and(eq(level,ERROR),eq(ack,true)))")
    assert query.filter == {"$nor": [{"$and": [{"level": "ERROR"}, {"ack": True}]}]}


def test_nested_logical_operators_keep_their_structure() -> None:
    """Logical operators nest as written, without flattening."""
    query = MongoQueryBuilder(Event).build_query(
        "or(and(eq(level,ERROR),not(eq(ack,true))),eq(count,0))"
    )
    assert query.filter == {
        "$or": [
            {"$and": [{"level": "ERROR"}, {"$nor": [{"ack": True}]}]},
            {"count": 0},
        ]
    }


def test_top_level_expressions_are_combined_with_and() -> None:
    """Expressions joined with `&` are all applied."""
    query = MongoQueryBuilder(Event).build_query("eq(level,ERROR)&gt(count,1)")
    assert query.filter == {"$and": [{"level": "ERROR"}, {"count": {"$gt": 1}}]}


def test_initial_query_filter_is_combined_with_the_rql_filter() -> None:
    """The RQL conditions are added with `$and` to the filter of the initial query."""
    initial = MongoQuery(filter={"organization_id": "ORG-1"})
    query = MongoQueryBuilder(Event).build_query("eq(level,ERROR)", initial_query=initial)
    assert query.filter == {"$and": [{"organization_id": "ORG-1"}, {"level": "ERROR"}]}


def test_initial_query_is_not_modified() -> None:
    """Building a query never changes the initial query passed by the caller."""
    initial = MongoQuery(filter={"organization_id": "ORG-1"}, sort=[("time", -1)])
    MongoQueryBuilder(Event).build_query("eq(level,ERROR)&order_by(count)", initial_query=initial)
    assert initial == MongoQuery(filter={"organization_id": "ORG-1"}, sort=[("time", -1)])


def test_query_without_filters_matches_everything() -> None:
    """An RQL expression with only `order_by` gives an empty filter."""
    query = MongoQueryBuilder(Event).build_query("order_by(time)")
    assert query == MongoQuery(filter={}, sort=[("time", 1)])
