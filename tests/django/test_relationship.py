import pytest
from django.db.models import Exists, OuterRef, Q, QuerySet

from requela.builders.django import DjangoQueryBuilder
from tests.django.models import Account, User
from tests.django.utils import assert_statements_equal


def test_comparison_eq_many_to_one():
    builder = DjangoQueryBuilder(User)
    query_string = "eq(account__name,My Account)"
    stmt = builder.build_query(query_string)
    expected = User.objects.filter(account__name="My Account")
    assert_statements_equal(stmt, expected)


def test_comparison_any_one_to_many():
    builder = DjangoQueryBuilder(Account)
    query_string = "any(users,eq(users.name,John))"
    stmt = builder.build_query(query_string)
    expected = Account.objects.filter(
        Exists(User.objects.filter(account=OuterRef("pk")).filter(name="John"))
    )
    assert_statements_equal(stmt, expected)


def test_comparison_any_one_to_many_complex_filter():
    builder = DjangoQueryBuilder(Account)
    query_string = "any(users,and(eq(users.name,John),gt(users.age,30)))"
    stmt = builder.build_query(query_string)
    expected = Account.objects.filter(
        Exists(User.objects.filter(account=OuterRef("pk")).filter(Q(name="John") & Q(age__gt=30)))
    )
    assert_statements_equal(stmt, expected)


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        (
            "and(eq(name,Acme),any(users,eq(users.name,John)))",
            Account.objects.filter(
                Q(name="Acme")
                & Q(Exists(User.objects.filter(account=OuterRef("pk")).filter(name="John")))
            ),
        ),
        (
            "or(eq(name,Acme),any(users,eq(users.name,John)))",
            Account.objects.filter(
                Q(name="Acme")
                | Q(Exists(User.objects.filter(account=OuterRef("pk")).filter(name="John")))
            ),
        ),
        (
            "not(any(users,eq(users.name,John)))",
            Account.objects.filter(
                ~Q(Exists(User.objects.filter(account=OuterRef("pk")).filter(name="John")))
            ),
        ),
    ],
)
def test_any_combines_with_logical_operators(query_string: str, expected: QuerySet) -> None:
    """`any()` can be nested inside `and`, `or` and `not` like any other condition."""
    stmt = DjangoQueryBuilder(Account).build_query(query_string)
    assert_statements_equal(stmt, expected)


def test_any_rejects_field_outside_the_relationship() -> None:
    """A field inside `any()` that is not reached through the relationship is rejected."""
    builder = DjangoQueryBuilder(Account)
    with pytest.raises(ValueError, match="Field 'name' is not part of relationship 'users'"):
        builder.build_query("any(users,eq(name,John))")


def test_any_rejects_nested_any() -> None:
    """`any()` inside another `any()` is rejected with a clear error."""
    builder = DjangoQueryBuilder(Account)
    with pytest.raises(ValueError, match="Nested any\\(\\) is not supported"):
        builder.build_query("any(users,and(any(users,eq(users.name,John))))")


@pytest.mark.parametrize(
    ("query_string", "expected_condition"),
    [
        (
            "any(users,or(eq(users.name,John),and(gt(users.age,30),eq(users.name,Jane))))",
            Q(name="John") | (Q(age__gt=30) & Q(name="Jane")),
        ),
        (
            "any(users,and(eq(users.name,John),not(gt(users.age,30))))",
            Q(name="John") & ~Q(age__gt=30),
        ),
    ],
)
def test_any_keeps_the_logical_structure_of_its_condition(
    query_string: str, expected_condition: Q
) -> None:
    """Nested `and`, `or` and `not` inside `any()` keep their structure in the subquery."""
    stmt = DjangoQueryBuilder(Account).build_query(query_string)
    expected = Account.objects.filter(
        Exists(User.objects.filter(account=OuterRef("pk")).filter(expected_condition))
    )
    assert_statements_equal(stmt, expected)
