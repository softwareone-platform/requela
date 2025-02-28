import pytest
from django.db.models import Q

from requela.builders.django import DjangoQueryBuilder
from tests.django.models import User
from tests.django.utils import assert_statements_equal


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("and(eq(name,John),eq(age,30))", User.objects.filter(Q(name="John") & Q(age=30))),
        (
            "and(eq(name,John),eq(age,30),eq(email,test@example.com))",
            User.objects.filter(Q(name="John") & Q(age=30) & Q(email="test@example.com")),
        ),
    ],
)
def test_logical_and(query_string, expected):
    builder = DjangoQueryBuilder(User)
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        (
            "or(eq(name,John),eq(age,30))",
            User.objects.filter(Q(name="John") | Q(age=30)),
        ),
        (
            "or(eq(name,John),eq(age,30),eq(email,test@example.com))",
            User.objects.filter(Q(name="John") | Q(age=30) | Q(email="test@example.com")),
        ),
    ],
)
def test_logical_or(query_string, expected):
    builder = DjangoQueryBuilder(User)
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


def test_logical_not():
    builder = DjangoQueryBuilder(User)
    stmt = builder.build_query("not(eq(name,John))")
    assert_statements_equal(stmt, User.objects.filter(~Q(name="John")))


def test_nested_logical():
    builder = DjangoQueryBuilder(User)
    stmt = builder.build_query("and(or(eq(name,John),eq(age,30)),eq(email,test@example.com))")
    assert_statements_equal(
        stmt,
        User.objects.filter((Q(name="John") | Q(age=30)) & Q(email="test@example.com")),
    )


def test_nested_logical_with_not():
    builder = DjangoQueryBuilder(User)
    stmt = builder.build_query(
        "and(or(eq(name,John),eq(age,30)),not(in(email,(test@example.com,test2@example.com))))"
    )
    assert_statements_equal(
        stmt,
        User.objects.filter(
            (Q(name="John") | Q(age=30)) & ~Q(email__in=["test@example.com", "test2@example.com"])
        ),
    )
