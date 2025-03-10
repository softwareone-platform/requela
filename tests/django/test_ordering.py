from requela.builders.django import DjangoQueryBuilder
from tests.django.models import User
from tests.django.utils import assert_statements_equal


def test_simple_order_by():
    builder = DjangoQueryBuilder(User)
    query_string = "order_by(name)"
    stmt = builder.build_query(query_string)
    expected = User.objects.order_by("name")
    assert_statements_equal(stmt, expected)


def test_simple_order_by_desc():
    builder = DjangoQueryBuilder(User)
    query_string = "order_by(-name)"
    stmt = builder.build_query(query_string)
    expected = User.objects.order_by("-name")
    assert_statements_equal(stmt, expected)


def test_order_by_multiple_fields():
    builder = DjangoQueryBuilder(User)
    query_string = "order_by(name,age)"
    stmt = builder.build_query(query_string)
    expected = User.objects.order_by("name", "age")
    assert_statements_equal(stmt, expected)


def test_order_by_multiple_fields_desc():
    builder = DjangoQueryBuilder(User)
    query_string = "order_by(+name,-age)"
    stmt = builder.build_query(query_string)
    expected = User.objects.order_by("name", "-age")
    assert_statements_equal(stmt, expected)


def test_order_by_with_filter():
    builder = DjangoQueryBuilder(User)
    query_string = "order_by(name)&eq(age,30)"
    stmt = builder.build_query(query_string)
    expected = User.objects.filter(age=30).order_by("name")
    assert_statements_equal(stmt, expected)
