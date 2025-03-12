import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum


class Base(DeclarativeBase):
    """Base class for all models"""


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class AccountStatus(int, enum.Enum):
    ACTIVE = 1
    INACTIVE = 0
    PENDING = 2


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="tenant")


class Actor(Base):
    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[AccountStatus] = mapped_column(SQLEnum(AccountStatus))
    balance: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    created_by: Mapped[Actor] = relationship(Actor)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("actors.id"))
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="accounts")
    users: Mapped[list["User"]] = relationship("User", back_populates="account")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String, nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole))
    is_active: Mapped[bool] = mapped_column(Boolean)
    birth_date: Mapped[date] = mapped_column(Date)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    account: Mapped[Account] = relationship("Account", back_populates="users")
