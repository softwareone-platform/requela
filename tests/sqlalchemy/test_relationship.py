from sqlalchemy import exists, select
from sqlalchemy.orm import aliased

from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder
from tests.sqlalchemy.models import Account, User
from tests.sqlalchemy.utils import assert_statements_equal


def test_comparison_eq_many_to_one():
    builder = SQLAlchemyQueryBuilder(User)
    query_string = "eq(account.name,My Account)"
    stmt = builder.build_query(query_string)
    alias = aliased(Account)
    expected = select(User).join(alias).filter(alias.name == "My Account")
    assert_statements_equal(stmt, expected)


def test_comparison_any_one_to_many():
    builder = SQLAlchemyQueryBuilder(Account)
    query_string = "any(users,eq(users.name,John))"
    stmt = builder.build_query(query_string)
    alias = aliased(User)
    expected = select(Account).filter(
        exists(alias).where(alias.account_id == Account.id, alias.name == "John")
    )
    assert_statements_equal(stmt, expected)


def test_comparison_any_one_to_many_complex_filter():
    builder = SQLAlchemyQueryBuilder(Account)
    query_string = "any(users,and(eq(users.name,John),gt(users.age,30)))"
    stmt = builder.build_query(query_string)
    alias = aliased(User)
    expected = select(Account).filter(
        exists(alias).where(
            alias.account_id == Account.id,
            alias.name == "John",
            alias.age > 30,
        )
    )
    assert_statements_equal(stmt, expected)
