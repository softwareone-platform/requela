from datetime import date, datetime

import pytest

from requela.dataclasses import Operator
from requela.rules import FieldRule, ModelRQLRules
from tests.django.models import User
from tests.django.rules import UserRules
from tests.django.utils import assert_statements_equal


def test_valid_field():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(name,Ratatouille 123)")
    assert_statements_equal(stmt, User.objects.filter(name="Ratatouille 123"))


def test_valid_aliased_field():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(events.born.at,2024-01-01)")
    assert_statements_equal(stmt, User.objects.filter(birth_date=date(2024, 1, 1)))


def test_invalid_field():
    user_filter = UserRules()
    with pytest.raises(ValueError):
        user_filter.build_query("eq(email,fail@example.com)")


def test_invalid_field_with_dot_notation():
    user_filter = UserRules()
    with pytest.raises(ValueError):
        user_filter.build_query("eq(norelationship.email,fail@example.com)")


def test_invalid_operator_for_field():
    user_filter = UserRules()
    with pytest.raises(ValueError, match="Operator 'eq' is not allowed for field 'role'."):
        user_filter.build_query("eq(role,admin)")


def test_valid_relationship():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(account.name,My Account)&order_by(name)")
    expected = User.objects.filter(account__name="My Account").order_by("name")
    assert_statements_equal(stmt, expected)


def test_valid_aliased_relationship():
    user_filter = UserRules()
    stmt = user_filter.build_query("eq(account.events.created.at,2025-01-01T12:10:00+00:00)")
    expected = User.objects.filter(
        account__created_at=datetime.fromisoformat("2025-01-01T12:10:00+00:00")
    )
    assert_statements_equal(stmt, expected)


def test_filter_class_validation_no_model():
    with pytest.raises(ValueError, match="UserRules must define __model__"):

        class UserRules(ModelRQLRules):
            pass


def test_filter_class_invalid_operator_for_field():
    class UserRules(ModelRQLRules):
        __model__ = User
        role = FieldRule(allowed_operators=[Operator.LTE, Operator.GTE])

    with pytest.raises(
        ValueError, match="Invalid operators 'gte', 'lte' for field 'role' of type 'str'."
    ):
        UserRules()


def test_filter_class_unexisting_field():
    class UserRules(ModelRQLRules):
        __model__ = User
        banana = FieldRule()

    with pytest.raises(ValueError, match="Field 'banana' not found in model 'User'."):
        UserRules()


def test_filter_class_order_field_not_allowed():
    class UserRules(ModelRQLRules):
        __model__ = User
        name = FieldRule(allow_ordering=False)

    with pytest.raises(ValueError, match="Order by 'name' is not allowed."):
        UserRules().build_query("order_by(name)")
