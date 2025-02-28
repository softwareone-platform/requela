from django.db.models import QuerySet


def assert_statements_equal(stmt: QuerySet, expected: QuerySet):
    assert stmt.query.sql_with_params() == expected.query.sql_with_params(), (
        f"\nSQL Parameters differ:\nActual:\n{stmt.query.sql_with_params()}\n"
        f"Expected:\n{expected.query.sql_with_params()}"
    )
