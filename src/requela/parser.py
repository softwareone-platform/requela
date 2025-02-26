from functools import lru_cache
from pathlib import Path

from lark import Lark, LarkError
from lark.tree import ParseTree

with open(Path(__file__).parent / "grammar.lark") as f:
    GRAMMAR = f.read()


PARSER = Lark(GRAMMAR, parser="lalr")


@lru_cache(maxsize=1000)
def parse(rql_query: str) -> ParseTree:
    try:
        return PARSER.parse(rql_query)
    except LarkError as e:
        raise ValueError(f"Invalid RQL query: {e}") from e
