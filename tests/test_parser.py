import pytest

from requela.parser import parse


def test_parser():
    ast = parse("eq(name,John)")
    assert ast is not None


def test_parser_invalid():
    with pytest.raises(ValueError, match="Invalid RQL query: Unexpected token"):
        parse("eq(name,John")
