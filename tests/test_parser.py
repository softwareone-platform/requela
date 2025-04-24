import pytest

from requela.parser import parse


def test_parser():
    ast = parse("eq(name,John)")
    assert ast is not None


def test_parser_with_quoted_string():
    ast = parse("eq(id,'000000-0d68-4494-a62e-2d4b6973bd37')")
    assert ast is not None


def test_parser_with_double_quoted_string():
    ast = parse('eq(name,"John Doe")')
    assert ast is not None


def test_parser_invalid():
    with pytest.raises(ValueError, match="Invalid RQL query: Unexpected token"):
        parse("eq(name,John")
