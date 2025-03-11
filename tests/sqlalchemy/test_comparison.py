from datetime import date, datetime

import pytest
from sqlalchemy import select

from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder
from tests.sqlalchemy.models import Account, User
from tests.sqlalchemy.utils import assert_statements_equal


# Equality tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "name", "Ratatouille 123", select(User).filter(User.name == "Ratatouille 123")),
        (User, "age", 25, select(User).filter(User.age == 25)),
        (Account, "balance", 25.13, select(Account).filter(Account.balance == 25.13)),
        (Account, "balance", -71.14, select(Account).filter(Account.balance == -71.14)),
        (Account, "balance", 33, select(Account).filter(Account.balance == 33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            select(User).filter(User.birth_date == date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            select(Account).filter(
                Account.created_at == datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
        (User, "is_active", "true", select(User).filter(User.is_active.is_(True))),
        (User, "is_active", "false", select(User).filter(User.is_active.is_(False))),
        (User, "name", "empty()", select(User).filter(User.name == "")),
        (User, "name", "null()", select(User).filter(User.name.is_(None))),
    ],
)
def test_comparison_eq(model, field, value, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"eq({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Not equal tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "name", "Ratatouille", select(User).filter(User.name != "Ratatouille")),
        (User, "age", 25, select(User).filter(User.age != 25)),
        (Account, "balance", 25.13, select(Account).filter(Account.balance != 25.13)),
        (Account, "balance", -71.14, select(Account).filter(Account.balance != -71.14)),
        (Account, "balance", 33, select(Account).filter(Account.balance != 33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            select(User).filter(User.birth_date != date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            select(Account).filter(
                Account.created_at != datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
        (User, "is_active", "true", select(User).filter(User.is_active.isnot(True))),
        (User, "is_active", "false", select(User).filter(User.is_active.isnot(False))),
        (User, "name", "empty()", select(User).filter(User.name != "")),
        (User, "name", "null()", select(User).filter(User.name.isnot(None))),
    ],
)
def test_comparison_ne(model, field, value, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"ne({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Less than tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, select(User).filter(User.age < 25)),
        (Account, "balance", 25.13, select(Account).filter(Account.balance < 25.13)),
        (Account, "balance", -71.14, select(Account).filter(Account.balance < -71.14)),
        (Account, "balance", 33, select(Account).filter(Account.balance < 33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            select(User).filter(User.birth_date < date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            select(Account).filter(
                Account.created_at < datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_lt(model, field, value, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"lt({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Greater than tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, select(User).filter(User.age > 25)),
        (Account, "balance", 25.13, select(Account).filter(Account.balance > 25.13)),
        (Account, "balance", -71.14, select(Account).filter(Account.balance > -71.14)),
        (Account, "balance", 33, select(Account).filter(Account.balance > 33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            select(User).filter(User.birth_date > date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            select(Account).filter(
                Account.created_at > datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_gt(model, field, value, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"gt({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Less than or equal tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, select(User).filter(User.age <= 25)),
        (Account, "balance", 25.13, select(Account).filter(Account.balance <= 25.13)),
        (Account, "balance", -71.14, select(Account).filter(Account.balance <= -71.14)),
        (Account, "balance", 33, select(Account).filter(Account.balance <= 33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            select(User).filter(User.birth_date <= date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            select(Account).filter(
                Account.created_at <= datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_lte(model, field, value, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"lte({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Greater than or equal tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, select(User).filter(User.age >= 25)),
        (Account, "balance", 25.13, select(Account).filter(Account.balance >= 25.13)),
        (Account, "balance", -71.14, select(Account).filter(Account.balance >= -71.14)),
        (Account, "balance", 33, select(Account).filter(Account.balance >= 33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            select(User).filter(User.birth_date >= date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            select(Account).filter(
                Account.created_at >= datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_gte(model, field, value, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"gte({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# In tests
@pytest.mark.parametrize(
    ("model", "field", "values", "expected"),
    [
        (User, "age", "(25,30,35)", select(User).filter(User.age.in_([25, 30, 35]))),
        (
            Account,
            "balance",
            "(25.13,50.00,75.25)",
            select(Account).filter(Account.balance.in_([25.13, 50.00, 75.25])),
        ),
        (
            User,
            "name",
            "(Alice,Bob,Charlie)",
            select(User).filter(User.name.in_(["Alice", "Bob", "Charlie"])),
        ),
    ],
)
def test_comparison_in(model, field, values, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"in({field},{values})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Out tests
@pytest.mark.parametrize(
    ("model", "field", "values", "expected"),
    [
        (User, "age", "(25,30,35)", select(User).filter(User.age.not_in([25, 30, 35]))),
        (
            Account,
            "balance",
            "(25.13,50.00,75.25)",
            select(Account).filter(Account.balance.not_in([25.13, 50.00, 75.25])),
        ),
        (
            User,
            "name",
            "(Alice,Bob,Charlie)",
            select(User).filter(User.name.not_in(["Alice", "Bob", "Charlie"])),
        ),
    ],
)
def test_comparison_out(model, field, values, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"out({field},{values})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Like tests
@pytest.mark.parametrize(
    ("model", "field", "pattern", "expected"),
    [
        (User, "name", "Rat*", select(User).filter(User.name.like("Rat%"))),
        (User, "name", "*ouille", select(User).filter(User.name.like("%ouille"))),
        (User, "name", "*atato*", select(User).filter(User.name.like("%atato%"))),
    ],
)
def test_comparison_like(model, field, pattern, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"like({field},{pattern})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# ILike tests
@pytest.mark.parametrize(
    ("model", "field", "pattern", "expected"),
    [
        (User, "name", "rat*", select(User).filter(User.name.ilike("rat%"))),
        (User, "name", "*OUILLE", select(User).filter(User.name.ilike("%OUILLE"))),
        (User, "name", "*AtAtO*", select(User).filter(User.name.ilike("%AtAtO%"))),
    ],
)
def test_comparison_ilike(model, field, pattern, expected):
    builder = SQLAlchemyQueryBuilder(model)
    query_string = f"ilike({field},{pattern})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


def test_with_initial_query():
    builder = SQLAlchemyQueryBuilder(User)
    initial = select(User).filter(User.age > 25)
    query_string = "eq(name,Ratatouille)"
    stmt = builder.build_query(query_string, initial)
    assert_statements_equal(stmt, select(User).filter(User.age > 25, User.name == "Ratatouille"))
