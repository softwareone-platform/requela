from django.db.models import Q

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
    expected = Account.objects.prefetch_related("users").filter(users__name="John")
    assert_statements_equal(stmt, expected)


def test_comparison_any_one_to_many_complex_filter():
    builder = DjangoQueryBuilder(Account)
    query_string = "any(users,and(eq(users.name,John),gt(users.age,30)))"
    stmt = builder.build_query(query_string)
    expected = Account.objects.prefetch_related("users").filter(
        Q(users__name="John") & Q(users__age__gt=30)
    )
    assert_statements_equal(stmt, expected)
