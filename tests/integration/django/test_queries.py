from collections.abc import Callable

import pytest

from requela.builders.django import DjangoQueryBuilder
from tests.django.models import Account, User
from tests.django.rules import AccountWithAliasedUsersRules, UserRules
from tests.integration.patterns import ILIKE_CASES, LIKE_CASES, USER_NAMES


@pytest.mark.parametrize(("pattern", "expected"), LIKE_CASES)
def test_like_selects_case_sensitive_matches(
    user_factory: Callable[..., User], pattern: str, expected: set[str]
) -> None:
    """`like` selects the names matching the pattern, case-sensitively."""
    for name in USER_NAMES:
        user_factory(name=name)

    queryset = DjangoQueryBuilder(User).build_query(f"like(name,{pattern})")

    assert {user.name for user in queryset} == expected


@pytest.mark.parametrize(("pattern", "expected"), ILIKE_CASES)
def test_ilike_selects_case_insensitive_matches(
    user_factory: Callable[..., User], pattern: str, expected: set[str]
) -> None:
    """`ilike` selects the names matching the pattern, ignoring case."""
    for name in USER_NAMES:
        user_factory(name=name)

    queryset = DjangoQueryBuilder(User).build_query(f"ilike(name,{pattern})")

    assert {user.name for user in queryset} == expected


def test_any_on_aliased_relationship_selects_accounts_with_a_matching_user(
    account_factory: Callable[..., Account], user_factory: Callable[..., User]
) -> None:
    """`any()` on a relationship alias selects the accounts having a matching user."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", account=acme)
    user_factory(name="Jane", account=globex)

    queryset = AccountWithAliasedUsersRules().build_query("any(members,eq(members.name,John))")

    assert [account.name for account in queryset] == ["Acme"]


def test_any_applies_all_conditions_to_the_same_related_row(
    account_factory: Callable[..., Account], user_factory: Callable[..., User]
) -> None:
    """`any()` selects an account only if one single user satisfies every condition."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", age=20, account=acme)
    user_factory(name="Jane", age=40, account=acme)
    user_factory(name="John", age=40, account=globex)

    queryset = AccountWithAliasedUsersRules().build_query(
        "any(members,and(eq(members.name,John),gt(members.age,30)))"
    )

    assert [account.name for account in queryset] == ["Globex"]


def test_many_to_one_field_selects_users_of_matching_account(
    account_factory: Callable[..., Account], user_factory: Callable[..., User]
) -> None:
    """A field through a many-to-one relationship filters on the related row."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", account=acme)
    user_factory(name="Jane", account=globex)

    queryset = UserRules().build_query("eq(account.name,Acme)")

    assert [user.name for user in queryset] == ["John"]


def test_order_by_sorts_descending_on_minus_prefix(user_factory: Callable[..., User]) -> None:
    """`order_by(-field)` returns the rows sorted by that field in descending order."""
    for name in ["Colette", "Alfredo", "Remy"]:
        user_factory(name=name)

    queryset = DjangoQueryBuilder(User).build_query("order_by(-name)")

    assert [user.name for user in queryset] == ["Remy", "Colette", "Alfredo"]


def test_any_inside_and_combines_with_other_conditions(
    account_factory: Callable[..., Account], user_factory: Callable[..., User]
) -> None:
    """`any()` inside `and()` selects rows matching both the `any()` and the other condition."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", account=acme)
    user_factory(name="John", account=globex)

    queryset = AccountWithAliasedUsersRules().build_query(
        "and(eq(name,Acme),any(members,eq(members.name,John)))"
    )

    assert [account.name for account in queryset] == ["Acme"]


def test_not_any_selects_rows_without_a_matching_related_row(
    account_factory: Callable[..., Account], user_factory: Callable[..., User]
) -> None:
    """`not(any())` selects the accounts with no matching user, including those without users."""
    acme = account_factory(name="Acme")
    account_factory(name="Globex")
    user_factory(name="John", account=acme)

    queryset = AccountWithAliasedUsersRules().build_query("not(any(members,eq(members.name,John)))")

    assert [account.name for account in queryset] == ["Globex"]


def test_separate_any_conditions_may_match_different_related_rows(
    account_factory: Callable[..., Account], user_factory: Callable[..., User]
) -> None:
    """Two separate `any()` conditions may be satisfied by two different users."""
    acme = account_factory(name="Acme")
    user_factory(name="John", age=20, account=acme)
    user_factory(name="Jane", age=40, account=acme)

    queryset = AccountWithAliasedUsersRules().build_query(
        "and(any(members,eq(members.name,John)),any(members,gt(members.age,30)))"
    )

    assert [account.name for account in queryset] == ["Acme"]


def test_any_returns_each_row_once_when_several_related_rows_match(
    account_factory: Callable[..., Account], user_factory: Callable[..., User]
) -> None:
    """`any()` returns an account once even when several of its users match."""
    acme = account_factory(name="Acme")
    user_factory(name="John", account=acme)
    user_factory(name="John", account=acme)

    queryset = AccountWithAliasedUsersRules().build_query("any(members,eq(members.name,John))")

    assert [account.name for account in queryset] == ["Acme"]
