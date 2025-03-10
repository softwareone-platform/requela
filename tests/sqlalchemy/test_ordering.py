from sqlalchemy import select

from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder
from tests.sqlalchemy.models import User
from tests.sqlalchemy.utils import assert_statements_equal


def test_simple_order_by():
    builder = SQLAlchemyQueryBuilder(User)
    query_string = "order_by(name)"
    stmt = builder.build_query(query_string)
    expected = select(User).order_by(User.name)
    assert_statements_equal(stmt, expected)


def test_simple_order_by_desc():
    builder = SQLAlchemyQueryBuilder(User)
    query_string = "order_by(-name)"
    stmt = builder.build_query(query_string)
    expected = select(User).order_by(User.name.desc())
    assert_statements_equal(stmt, expected)


def test_order_by_multiple_fields():
    builder = SQLAlchemyQueryBuilder(User)
    query_string = "order_by(name,age)"
    stmt = builder.build_query(query_string)
    expected = select(User).order_by(User.name, User.age)
    assert_statements_equal(stmt, expected)


def test_order_by_multiple_fields_desc():
    builder = SQLAlchemyQueryBuilder(User)
    query_string = "order_by(+name,-age)"
    stmt = builder.build_query(query_string)
    expected = select(User).order_by(User.name, User.age.desc())
    assert_statements_equal(stmt, expected)


def test_order_by_with_filter():
    builder = SQLAlchemyQueryBuilder(User)
    query_string = "order_by(name)&eq(age,30)"
    stmt = builder.build_query(query_string)
    expected = select(User).filter(User.age == 30).order_by(User.name)
    assert_statements_equal(stmt, expected)
