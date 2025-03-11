from datetime import date, datetime

import pytest

from requela.builders.django import DjangoQueryBuilder
from tests.django.models import Account, User
from tests.django.utils import assert_statements_equal


# Equality tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "name", "Ratatouille 123", User.objects.filter(name="Ratatouille 123")),
        (User, "age", 25, User.objects.filter(age=25)),
        (Account, "balance", 25.13, Account.objects.filter(balance=25.13)),
        (Account, "balance", -71.14, Account.objects.filter(balance=-71.14)),
        (Account, "balance", 33, Account.objects.filter(balance=33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            User.objects.filter(birth_date=date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            Account.objects.filter(created_at=datetime.fromisoformat("2025-01-01T12:10:00+00:00")),
        ),
        (User, "is_active", "true", User.objects.filter(is_active=True)),
        (User, "is_active", "false", User.objects.filter(is_active=False)),
        (User, "name", "empty()", User.objects.filter(name="")),
        (User, "name", "null()", User.objects.filter(name__isnull=True)),
    ],
)
def test_comparison_eq(model, field, value, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"eq({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Not equal tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "name", "Ratatouille", User.objects.exclude(name="Ratatouille")),
        (User, "age", 25, User.objects.exclude(age=25)),
        (Account, "balance", 25.13, Account.objects.exclude(balance=25.13)),
        (Account, "balance", -71.14, Account.objects.exclude(balance=-71.14)),
        (Account, "balance", 33, Account.objects.exclude(balance=33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            User.objects.exclude(birth_date=date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            Account.objects.exclude(created_at=datetime.fromisoformat("2025-01-01T12:10:00+00:00")),
        ),
        (User, "is_active", "true", User.objects.exclude(is_active=True)),
        (User, "is_active", "false", User.objects.exclude(is_active=False)),
        (User, "name", "empty()", User.objects.exclude(name="")),
        (User, "name", "null()", User.objects.filter(name__isnull=False)),
    ],
)
def test_comparison_ne(model, field, value, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"ne({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Less than tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, User.objects.filter(age__lt=25)),
        (Account, "balance", 25.13, Account.objects.filter(balance__lt=25.13)),
        (Account, "balance", -71.14, Account.objects.filter(balance__lt=-71.14)),
        (Account, "balance", 33, Account.objects.filter(balance__lt=33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            User.objects.filter(birth_date__lt=date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            Account.objects.filter(
                created_at__lt=datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_lt(model, field, value, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"lt({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Greater than tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, User.objects.filter(age__gt=25)),
        (Account, "balance", 25.13, Account.objects.filter(balance__gt=25.13)),
        (Account, "balance", -71.14, Account.objects.filter(balance__gt=-71.14)),
        (Account, "balance", 33, Account.objects.filter(balance__gt=33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            User.objects.filter(birth_date__gt=date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            Account.objects.filter(
                created_at__gt=datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_gt(model, field, value, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"gt({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Less than or equal tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, User.objects.filter(age__lte=25)),
        (Account, "balance", 25.13, Account.objects.filter(balance__lte=25.13)),
        (Account, "balance", -71.14, Account.objects.filter(balance__lte=-71.14)),
        (Account, "balance", 33, Account.objects.filter(balance__lte=33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            User.objects.filter(birth_date__lte=date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            Account.objects.filter(
                created_at__lte=datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_lte(model, field, value, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"lte({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Greater than or equal tests
@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "age", 25, User.objects.filter(age__gte=25)),
        (Account, "balance", 25.13, Account.objects.filter(balance__gte=25.13)),
        (Account, "balance", -71.14, Account.objects.filter(balance__gte=-71.14)),
        (Account, "balance", 33, Account.objects.filter(balance__gte=33)),
        (
            User,
            "birth_date",
            "1974-06-29",
            User.objects.filter(birth_date__gte=date(1974, 6, 29)),
        ),
        (
            Account,
            "created_at",
            "2025-01-01T12:10:00+00:00",
            Account.objects.filter(
                created_at__gte=datetime.fromisoformat("2025-01-01T12:10:00+00:00")
            ),
        ),
    ],
)
def test_comparison_gte(model, field, value, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"gte({field},{value})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# In tests
@pytest.mark.parametrize(
    ("model", "field", "values", "expected"),
    [
        (User, "age", "(25,30,35)", User.objects.filter(age__in=[25, 30, 35])),
        (
            Account,
            "balance",
            "(25.13,50.00,75.25)",
            Account.objects.filter(balance__in=[25.13, 50.00, 75.25]),
        ),
        (
            User,
            "name",
            "(Alice,Bob,Charlie)",
            User.objects.filter(name__in=["Alice", "Bob", "Charlie"]),
        ),
    ],
)
def test_comparison_in(model, field, values, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"in({field},{values})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Out tests
@pytest.mark.parametrize(
    ("model", "field", "values", "expected"),
    [
        (User, "age", "(25,30,35)", User.objects.exclude(age__in=[25, 30, 35])),
        (
            Account,
            "balance",
            "(25.13,50.00,75.25)",
            Account.objects.exclude(balance__in=[25.13, 50.00, 75.25]),
        ),
        (
            User,
            "name",
            "(Alice,Bob,Charlie)",
            User.objects.exclude(name__in=["Alice", "Bob", "Charlie"]),
        ),
    ],
)
def test_comparison_out(model, field, values, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"out({field},{values})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# Like tests
@pytest.mark.parametrize(
    ("model", "field", "pattern", "expected"),
    [
        (User, "name", "Rat*", User.objects.filter(name__startswith="Rat")),
        (User, "name", "*ouille", User.objects.filter(name__endswith="ouille")),
        (User, "name", "*atato*", User.objects.filter(name__contains="atato")),
        (User, "name", "atato", User.objects.filter(name__contains="atato")),
    ],
)
def test_comparison_like(model, field, pattern, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"like({field},{pattern})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


# ILike tests
@pytest.mark.parametrize(
    ("model", "field", "pattern", "expected"),
    [
        (User, "name", "rat*", User.objects.filter(name__startswith="rat")),
        (User, "name", "*OUILLE", User.objects.filter(name__endswith="OUILLE")),
        (User, "name", "*AtAtO*", User.objects.filter(name__contains="AtAtO")),
        (User, "name", "AtAtO", User.objects.filter(name__contains="AtAtO")),
    ],
)
def test_comparison_ilike(model, field, pattern, expected):
    builder = DjangoQueryBuilder(model)
    query_string = f"ilike({field},{pattern})"
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


def test_with_initial_query():
    builder = DjangoQueryBuilder(User)
    initial = User.objects.filter(age__gt=25)
    query_string = "eq(name,Ratatouille)"
    stmt = builder.build_query(query_string, initial)
    assert_statements_equal(stmt, User.objects.filter(age__gt=25, name="Ratatouille"))
