from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime

import pytest
from django.db import connection, transaction

from tests.django.models import Account, AccountStatus, User, UserRole


@pytest.fixture(scope="session")
def django_database() -> Iterator[None]:
    """A PostgreSQL test database with the tables of the Django test models."""
    database_name = connection.settings_dict["NAME"]
    connection.creation.create_test_db(verbosity=0, autoclobber=True)
    yield
    connection.creation.destroy_test_db(database_name, verbosity=0)


@pytest.fixture(autouse=True)
def _rollback_changes(django_database: None) -> Iterator[None]:
    """Roll back the database changes made by each test."""
    with transaction.atomic():
        yield
        transaction.set_rollback(True)


@pytest.fixture
def account_factory() -> Callable[..., Account]:
    """Build and persist an `Account` with overridable defaults."""

    def _build(
        *,
        name: str = "Acme",
        status: AccountStatus = AccountStatus.ACTIVE,
        balance: float = 0.0,
    ) -> Account:
        return Account.objects.create(
            name=name,
            status=status,
            balance=balance,
            created_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        )

    return _build


@pytest.fixture
def user_factory(account_factory: Callable[..., Account]) -> Callable[..., User]:
    """Build and persist a `User` with overridable defaults; creates an account if needed."""

    def _build(
        *,
        name: str = "John",
        age: int = 30,
        account: Account | None = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> User:
        return User.objects.create(
            name=name,
            age=age,
            account=account or account_factory(),
            role=role,
            is_active=is_active,
            birth_date=date(1990, 1, 1),
        )

    return _build
