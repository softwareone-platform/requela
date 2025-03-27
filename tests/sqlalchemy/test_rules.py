from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import aliased

from requela.dataclasses import Operator
from requela.exceptions import RequelaError
from requela.rules import FieldRule, ModelRQLRules
from tests.sqlalchemy.models import Account, Actor, User
from tests.sqlalchemy.rules import AccountRules, UserRules
from tests.sqlalchemy.utils import assert_statements_equal


def test_valid_field():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(name,Ratatouille 123)")
    assert_statements_equal(stmt, select(User).filter(User.name == "Ratatouille 123"))


def test_with_uuid():
    myfilter = AccountRules()
    stmt = myfilter.build_query("eq(datasource_id,90575008-bdde-4a40-ab07-82be547674e6)")
    assert_statements_equal(
        stmt,
        select(Account).filter(Account.datasource_id == "90575008-bdde-4a40-ab07-82be547674e6"),
    )


def test_valid_aliased_field():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(events.born.at,2024-01-01)")
    assert_statements_equal(stmt, select(User).filter(User.birth_date == date(2024, 1, 1)))


def test_invalid_field():
    user_filter = UserRules()
    with pytest.raises(RequelaError):
        user_filter.build_query("eq(email,fail@example.com)")


def test_invalid_field_with_dot_notation():
    user_filter = UserRules()
    with pytest.raises(RequelaError):
        user_filter.build_query("eq(norelationship.email,fail@example.com)")


def test_invalid_operator_for_field():
    user_filter = UserRules()
    with pytest.raises(RequelaError, match="Operator 'eq' is not allowed for field 'role'."):
        user_filter.build_query("eq(role,admin)")


def test_valid_relationship():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(account.name,My Account)&order_by(name)")
    alias = aliased(Account)
    expected = select(User).join(alias).filter(alias.name == "My Account").order_by(User.name)
    assert_statements_equal(stmt, expected)


def test_valid_alias_on_relationship():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(account.events.created.at,2025-01-01T12:10:00+00:00)")
    alias = aliased(Account)
    expected = (
        select(User)
        .join(alias)
        .filter(alias.created_at == datetime.fromisoformat("2025-01-01T12:10:00+00:00"))
    )
    assert_statements_equal(stmt, expected)


def test_valid_aliased_relationship():
    account_filter = AccountRules()
    stmt = account_filter.build_query("eq(events.created.by.name,John Doe)")
    alias = aliased(Actor)
    expected = (
        select(Account)
        .join(alias, onclause=alias.id == Account.created_by_id)
        .filter(alias.name == "John Doe")
    )
    assert_statements_equal(stmt, expected)


def test_filter_class_validation_no_model():
    with pytest.raises(TypeError, match="UserRules must define __model__"):

        class UserRules(ModelRQLRules):
            pass


def test_filter_class_invalid_operator_for_field():
    class UserRules(ModelRQLRules):
        __model__ = User
        role = FieldRule(allowed_operators=[Operator.LTE, Operator.GTE])

    with pytest.raises(ExceptionGroup, match="Model validation failed for 'User'") as exc:
        UserRules()

    assert [(e.__class__, str(e)) for e in exc.value.exceptions] == [
        (ValueError, "Invalid operators 'gte', 'lte' for field 'role' of type 'UserRole'."),
    ]


def test_filter_class_unexisting_field():
    class UserRules(ModelRQLRules):
        __model__ = User
        banana = FieldRule()

    with pytest.raises(ExceptionGroup, match="Model validation failed for 'User'") as exc:
        UserRules()

    assert [(e.__class__, str(e)) for e in exc.value.exceptions] == [
        (ValueError, "Field 'banana' not found in model 'User'."),
    ]


def test_multiple_exceptions_raised():
    class UserRules(ModelRQLRules):
        __model__ = User
        role = FieldRule(allowed_operators=[Operator.LTE, Operator.GTE])
        banana = FieldRule()

    with pytest.raises(ExceptionGroup, match="Model validation failed for 'User'") as exc:
        UserRules()

    assert [(e.__class__, str(e)) for e in exc.value.exceptions] == [
        (ValueError, "Field 'banana' not found in model 'User'."),
        (ValueError, "Invalid operators 'gte', 'lte' for field 'role' of type 'UserRole'."),
    ]


def test_filter_class_order_field_not_allowed():
    class UserRules(ModelRQLRules):
        __model__ = User
        name = FieldRule(allow_ordering=False)

    with pytest.raises(RequelaError, match="Order by 'name' is not allowed."):
        UserRules().build_query("order_by(name)")


def test_get_documentation():
    docs = UserRules().get_documentation()
    assert docs.split("\n") == [
        "| Field | Operators | Order By |",
        "|-------|-----------|----------|",
        "|account.balance|eq, gt, gte, in, lt, lte, ne, out|yes|",
        "|account.datasource_id|eq, ilike, in, like, ne, out|yes|",
        "|account.description|eq, ilike, in, like, ne, out|yes|",
        "|account.events.created.at|eq, gt, gte, lt, lte, ne|yes|",
        "|account.events.created.by.name|eq, ilike, in, like, ne, out|yes|",
        "|account.events.created.by|eq, ne|no|",
        "|account.name|eq, ilike, in, like, ne, out|yes|",
        "|account.status|eq, in, ne, out|yes|",
        "|account.tenant.name|eq, ilike, in, like, ne, out|yes|",
        "|account.tenant|eq, ne|no|",
        "|account|eq, ne|no|",
        "|events.born.at|eq, gt, gte, lt, lte, ne|yes|",
        "|is_active|eq, ne|yes|",
        "|name|eq, ilike, in, like, ne, out|yes|",
        "|role|in, out|yes|",
    ]


def test_tenant_relationship_eq_null():
    account_rules = AccountRules()
    stmt = account_rules.build_query("eq(tenant,null())")
    assert_statements_equal(stmt, select(Account).filter(Account.tenant_id.is_(None)))


def test_tenant_relationship_eq_invalid_value():
    account_rules = AccountRules()
    with pytest.raises(
        RequelaError, match="`eq` can be applied to relationship only to test for null."
    ):
        account_rules.build_query("eq(tenant,3)")


def test_tenant_relationship_ne_null():
    account_rules = AccountRules()
    stmt = account_rules.build_query("ne(tenant,null())")
    assert_statements_equal(stmt, select(Account).filter(Account.tenant_id.isnot(None)))


def test_tenant_relationship_ne_invalid_value():
    account_rules = AccountRules()
    with pytest.raises(
        RequelaError, match="`ne` can be applied to relationship only to test for null."
    ):
        account_rules.build_query("ne(tenant,pip)")
