from collections.abc import Callable, Iterator
from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from tests.settings import DATABASE_URL
from tests.sqlalchemy.models import Account, AccountStatus, Actor, Base, Tenant, User, UserRole


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """An engine bound to the PostgreSQL test database, with the test schema created."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose changes are rolled back at the end of the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def actor(session: Session) -> Actor:
    """The actor that creates the test accounts."""
    actor = Actor(name="Skinner")
    session.add(actor)
    session.flush()
    return actor


@pytest.fixture
def tenant_factory(session: Session) -> Callable[..., Tenant]:
    """Build and persist a `Tenant` with overridable defaults."""

    def _build(*, name: str = "Gusteau's") -> Tenant:
        tenant = Tenant(name=name)
        session.add(tenant)
        session.flush()
        return tenant

    return _build


@pytest.fixture
def account_factory(session: Session, actor: Actor) -> Callable[..., Account]:
    """Build and persist an `Account` with overridable defaults."""

    def _build(
        *,
        name: str = "Acme",
        status: AccountStatus = AccountStatus.ACTIVE,
        balance: float = 0.0,
        tenant: Tenant | None = None,
    ) -> Account:
        account = Account(
            name=name,
            status=status,
            balance=balance,
            created_at=datetime(2025, 1, 1, 12, 0),
            created_by=actor,
            tenant=tenant,
            datasource_id=str(uuid4()),
        )
        session.add(account)
        session.flush()
        return account

    return _build


@pytest.fixture
def user_factory(session: Session, account_factory: Callable[..., Account]) -> Callable[..., User]:
    """Build and persist a `User` with overridable defaults; creates an account if needed."""

    def _build(
        *,
        name: str = "John",
        age: int = 30,
        account: Account | None = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> User:
        user = User(
            name=name,
            age=age,
            account=account or account_factory(),
            role=role,
            is_active=is_active,
            birth_date=date(1990, 1, 1),
        )
        session.add(user)
        session.flush()
        return user

    return _build
