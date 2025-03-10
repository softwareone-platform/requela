import pytest
from sqlalchemy import and_, or_, select

from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder
from tests.sqlalchemy.models import User
from tests.sqlalchemy.utils import assert_statements_equal


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("and(eq(name,John),eq(age,30))", select(User).filter(User.name == "John", User.age == 30)),
        (
            "and(eq(name,John),eq(age,30),eq(email,test@example.com))",
            select(User).filter(
                User.name == "John", User.age == 30, User.email == "test@example.com"
            ),
        ),
    ],
)
def test_logical_and(query_string, expected):
    builder = SQLAlchemyQueryBuilder(User)
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        (
            "or(eq(name,John),eq(age,30))",
            select(User).filter(or_(User.name == "John", User.age == 30)),
        ),
        (
            "or(eq(name,John),eq(age,30),eq(email,test@example.com))",
            select(User).filter(
                or_(User.name == "John", User.age == 30, User.email == "test@example.com")
            ),
        ),
    ],
)
def test_logical_or(query_string, expected):
    builder = SQLAlchemyQueryBuilder(User)
    stmt = builder.build_query(query_string)
    assert_statements_equal(stmt, expected)


def test_logical_not():
    builder = SQLAlchemyQueryBuilder(User)
    stmt = builder.build_query("not(eq(name,John))")
    assert_statements_equal(stmt, select(User).filter(User.name != "John"))


def test_nested_logical():
    builder = SQLAlchemyQueryBuilder(User)
    stmt = builder.build_query("and(or(eq(name,John),eq(age,30)),eq(email,test@example.com))")
    assert_statements_equal(
        stmt,
        select(User).filter(
            and_(or_(User.name == "John", User.age == 30), User.email == "test@example.com")
        ),
    )


def test_nested_logical_with_not():
    builder = SQLAlchemyQueryBuilder(User)
    stmt = builder.build_query(
        "and(or(eq(name,John),eq(age,30)),not(in(email,(test@example.com,test2@example.com))))"
    )
    assert_statements_equal(
        stmt,
        select(User).filter(
            and_(
                or_(User.name == "John", User.age == 30),
                User.email.notin_(["test@example.com", "test2@example.com"]),
            )
        ),
    )
