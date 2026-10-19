from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder
from tests.integration.patterns import ILIKE_CASES, LIKE_CASES, USER_NAMES
from tests.sqlalchemy.models import Account, Tenant, User
from tests.sqlalchemy.rules import (
    AccountWithAliasedUsersRules,
    AccountWithPrefixedRelationsRules,
    UserRules,
)


@pytest.mark.parametrize(("pattern", "expected"), LIKE_CASES)
def test_like_selects_case_sensitive_matches(
    session: Session, user_factory: Callable[..., User], pattern: str, expected: set[str]
) -> None:
    """`like` selects the names matching the pattern, case-sensitively."""
    for name in USER_NAMES:
        user_factory(name=name)

    stmt = SQLAlchemyQueryBuilder(User).build_query(f"like(name,{pattern})")

    assert {user.name for user in session.scalars(stmt)} == expected


@pytest.mark.parametrize(("pattern", "expected"), ILIKE_CASES)
def test_ilike_selects_case_insensitive_matches(
    session: Session, user_factory: Callable[..., User], pattern: str, expected: set[str]
) -> None:
    """`ilike` selects the names matching the pattern, ignoring case."""
    for name in USER_NAMES:
        user_factory(name=name)

    stmt = SQLAlchemyQueryBuilder(User).build_query(f"ilike(name,{pattern})")

    assert {user.name for user in session.scalars(stmt)} == expected


def test_any_on_aliased_relationship_selects_accounts_with_a_matching_user(
    session: Session,
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """`any()` on a relationship alias selects the accounts having a matching user."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", account=acme)
    user_factory(name="Jane", account=globex)

    stmt = AccountWithAliasedUsersRules().build_query("any(members,eq(members.name,John))")

    assert [account.name for account in session.scalars(stmt)] == ["Acme"]


def test_any_applies_all_conditions_to_the_same_related_row(
    session: Session,
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """`any()` selects an account only if one single user satisfies every condition."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", age=20, account=acme)
    user_factory(name="Jane", age=40, account=acme)
    user_factory(name="John", age=40, account=globex)

    stmt = AccountWithAliasedUsersRules().build_query(
        "any(members,and(eq(members.name,John),gt(members.age,30)))"
    )

    assert [account.name for account in session.scalars(stmt)] == ["Globex"]


def test_relationship_alias_prefixing_another_selects_matching_accounts(
    session: Session,
    tenant_factory: Callable[..., Tenant],
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """Relationship aliases 'tenant' and 'tenants' each filter on their own relationship."""
    acme = account_factory(name="Acme", tenant=tenant_factory(name="Gusteau's"))
    globex = account_factory(name="Globex")
    user_factory(name="John", account=globex)
    rules = AccountWithPrefixedRelationsRules()

    by_tenant = rules.build_query("eq(tenant.name,Gusteau's)")
    by_user = rules.build_query("any(tenants,eq(tenants.name,John))")

    assert [account.name for account in session.scalars(by_tenant)] == [acme.name]
    assert [account.name for account in session.scalars(by_user)] == [globex.name]


def test_many_to_one_field_selects_users_of_matching_account(
    session: Session,
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """A field through a many-to-one relationship joins it and filters on the related row."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", account=acme)
    user_factory(name="Jane", account=globex)

    stmt = UserRules().build_query("eq(account.name,Acme)")

    assert [user.name for user in session.scalars(stmt)] == ["John"]


def test_order_by_sorts_descending_on_minus_prefix(
    session: Session, user_factory: Callable[..., User]
) -> None:
    """`order_by(-field)` returns the rows sorted by that field in descending order."""
    for name in ["Colette", "Alfredo", "Remy"]:
        user_factory(name=name)

    stmt = SQLAlchemyQueryBuilder(User).build_query("order_by(-name)")

    assert [user.name for user in session.scalars(stmt)] == ["Remy", "Colette", "Alfredo"]


def test_any_inside_and_combines_with_other_conditions(
    session: Session,
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """`any()` inside `and()` selects rows matching both the `any()` and the other condition."""
    acme = account_factory(name="Acme")
    globex = account_factory(name="Globex")
    user_factory(name="John", account=acme)
    user_factory(name="John", account=globex)

    stmt = AccountWithAliasedUsersRules().build_query(
        "and(eq(name,Acme),any(members,eq(members.name,John)))"
    )

    assert [account.name for account in session.scalars(stmt)] == ["Acme"]


def test_not_any_selects_rows_without_a_matching_related_row(
    session: Session,
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """`not(any())` selects the accounts with no matching user, including those without users."""
    acme = account_factory(name="Acme")
    account_factory(name="Globex")
    user_factory(name="John", account=acme)

    stmt = AccountWithAliasedUsersRules().build_query("not(any(members,eq(members.name,John)))")

    assert [account.name for account in session.scalars(stmt)] == ["Globex"]


def test_separate_any_conditions_may_match_different_related_rows(
    session: Session,
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """Two separate `any()` conditions may be satisfied by two different users."""
    acme = account_factory(name="Acme")
    user_factory(name="John", age=20, account=acme)
    user_factory(name="Jane", age=40, account=acme)

    stmt = AccountWithAliasedUsersRules().build_query(
        "and(any(members,eq(members.name,John)),any(members,gt(members.age,30)))"
    )

    assert [account.name for account in session.scalars(stmt)] == ["Acme"]


def test_any_returns_each_row_once_when_several_related_rows_match(
    session: Session,
    account_factory: Callable[..., Account],
    user_factory: Callable[..., User],
) -> None:
    """`any()` returns an account once even when several of its users match."""
    acme = account_factory(name="Acme")
    user_factory(name="John", account=acme)
    user_factory(name="John", account=acme)

    stmt = AccountWithAliasedUsersRules().build_query("any(members,eq(members.name,John))")

    assert [account.name for account in session.scalars(stmt)] == ["Acme"]
