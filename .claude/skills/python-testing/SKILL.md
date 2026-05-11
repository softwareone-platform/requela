---
name: python-testing
description: Write and review high-quality Python tests for ReQueLa using pytest. Use whenever creating new tests, refactoring existing tests, debugging test failures, improving coverage, or adding cases for new grammar/operators/builders — even when the user says "tests" without further detail. Enforces parallel SQLAlchemy and Django suites, comparison via `assert_statements_equal` against a hand-built ORM expression, mandatory type annotations and docstrings on new tests, parametrized `(model, field, value, expected)` cases, fixtures kept out of test files (in `conftest.py` or modules it imports), ≥90% coverage (target ≥95%), and testing only public interfaces — never private functions or modules.
---

# Writing Effective ReQueLa Tests

This skill defines how tests should be written for ReQueLa. Every test must be **atomic**, **self-contained**, **typed**, **documented**, and verify a **single public behavior** of the parser, transformer, rules layer, or one of the two backend builders. Tests that wander, repeat themselves, or reach into private internals are a maintenance liability — when they break, nobody knows what they were trying to prove.

ReQueLa has no network or I/O surface: the library is a pure pipeline of `RQL string → Lark AST → backend-specific query object`. That shapes everything below — there is no HTTP to mock, no database to spin up, no clock to freeze. Tests assert that an input expression compiles to the **same SQL/QuerySet** as a hand-built ORM expression.

## Non-negotiables

These rules apply to every test in the project. If you find yourself wanting to break one, that's a signal the design is off, not the rule.

1. **Shared behavior is tested in both backends.** If you change the grammar, transformer, rules layer, or anything in `OperatorFunctions`, you must add/update tests under **both** `tests/sqlalchemy/` and `tests/django/`. The files are deliberately parallel — see [`CLAUDE.md`](../../../CLAUDE.md).
2. **Compare statements with `assert_statements_equal`** — never compare raw strings, never inspect internal builder state. See [`tests/sqlalchemy/utils.py`](../../../tests/sqlalchemy/utils.py) and [`tests/django/utils.py`](../../../tests/django/utils.py).
3. **Fixtures live in `conftest.py`** or in modules that `conftest.py` imports. They never live inside test files. Test models and rule classes (`tests/<backend>/models.py`, `tests/<backend>/rules.py`) are imported directly by tests — they are stable reference data, not fixtures.
4. **Type annotations are mandatory on all new tests** — including return type `-> None`. This matches the project rule in [`CLAUDE.md`](../../../CLAUDE.md) ("Type annotations are mandatory on all functions and parameters"). Existing untyped tests are grandfathered; do not retrofit en masse, but type any test you touch substantively.
5. **Every new test has a one-sentence docstring** stating the behavior under test.
6. **Test only public interfaces.** Never call into `_private` functions, methods, or modules (e.g. `Rules._resolve_alias`, `Rules._validate_operator_and_field` are private callbacks — exercise them through `build_query()`).
7. **Coverage must be ≥ 90 %**, target ≥ 95 %. CI runs `--cov=requela`; do not lower thresholds to make a change pass.

The rest of this skill explains how to satisfy each rule and gives the standard ReQueLa patterns.

---

## Where each test goes

ReQueLa's pipeline maps directly onto where tests live:

| Layer | What to test there | File |
|---|---|---|
| Grammar + transformer | Parse-only behavior: terminals, literals (`null()`, `empty()`, UUIDs, dates), syntax errors | [`tests/test_parser.py`](../../../tests/test_parser.py) |
| SQLAlchemy backend | `SQLAlchemyQueryBuilder.build_query()` against `tests/sqlalchemy/models.py` | [`tests/sqlalchemy/`](../../../tests/sqlalchemy/) |
| Django backend | Django builder against `tests/django/models.py` | [`tests/django/`](../../../tests/django/) |
| Rules layer (`ModelRQLRules`) | Alias resolution, operator/field validation, ordering whitelist, documentation output | `tests/<backend>/test_rules.py` |

The five files under each backend mirror each other 1:1 — `test_comparison.py`, `test_logical.py`, `test_ordering.py`, `test_relationship.py`, `test_rules.py`. **A shared-behavior change should produce a diff in both directory trees.** If only one side changes, justify it explicitly in the PR (e.g. the change is genuinely backend-specific).

For the grammar/transformer layer in `tests/test_parser.py`, neither ORM is loaded — keep tests there ORM-free.

---

## The ReQueLa assertion pattern

Every backend test follows the same shape: build a statement from an RQL string, then assert it equals a hand-written ORM expression that produces the same SQL.

### SQLAlchemy

```python
from sqlalchemy import select

from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder
from tests.sqlalchemy.models import User
from tests.sqlalchemy.utils import assert_statements_equal


def test_comparison_eq_string_field() -> None:
    """`eq(name,...)` compiles to `User.name == ...` against `User`."""
    builder = SQLAlchemyQueryBuilder(User)
    stmt = builder.build_query("eq(name,Ratatouille)")
    assert_statements_equal(stmt, select(User).filter(User.name == "Ratatouille"))
```

### Django

```python
from tests.django.models import User
from tests.django.utils import assert_statements_equal
from requela.builders.django import DjangoQueryBuilder


def test_comparison_eq_string_field() -> None:
    """`eq(name,...)` compiles to `User.objects.filter(name=...)`."""
    builder = DjangoQueryBuilder(User)
    qs = builder.build_query("eq(name,Ratatouille)")
    assert_statements_equal(qs, User.objects.filter(name="Ratatouille"))
```

### What the helpers actually check

- SQLAlchemy: the compiled SQL string **and** the bound parameter dict match. See [`tests/sqlalchemy/utils.py`](../../../tests/sqlalchemy/utils.py).
- Django: `query.sql_with_params()` matches. See [`tests/django/utils.py`](../../../tests/django/utils.py).

Never roll your own comparison — extend these helpers if you need more (and update both sides if you do).

### Don't snapshot raw SQL strings

If you ever feel like writing `assert str(stmt.compile()) == "SELECT users..."`, stop. Hand-build the expected expression with the ORM itself — that way the test stays valid across SQLAlchemy/Django dialect changes and reads like the production code it's exercising.

---

## Parametrize variations of the same concept

ReQueLa's operator tests are naturally tabular. The established pattern is `(model, field, value, expected)` tuples — see [`tests/sqlalchemy/test_comparison.py`](../../../tests/sqlalchemy/test_comparison.py). Use it.

```python
import pytest
from sqlalchemy import select

from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder
from tests.sqlalchemy.models import Account, User
from tests.sqlalchemy.utils import assert_statements_equal


@pytest.mark.parametrize(
    ("model", "field", "value", "expected"),
    [
        (User, "name", "Ratatouille", select(User).filter(User.name == "Ratatouille")),
        (User, "age", 25, select(User).filter(User.age == 25)),
        (Account, "balance", 25.13, select(Account).filter(Account.balance == 25.13)),
        (User, "name", "null()", select(User).filter(User.name.is_(None))),
        (User, "name", "empty()", select(User).filter(User.name == "")),
    ],
)
def test_comparison_eq(
    model: type, field: str, value: object, expected: object
) -> None:
    """`eq(<field>,<value>)` compiles to the equivalent ORM filter."""
    builder = SQLAlchemyQueryBuilder(model)
    stmt = builder.build_query(f"eq({field},{value})")
    assert_statements_equal(stmt, expected)
```

Parametrize when the cases exercise the **same** logic with different inputs (an operator over different field types). Don't smuggle distinct behaviors into one parameterized test — if two cases would need different setup, different assertions, or different docstrings, split them. Test names like `test_<op>_and_<other_op>` are a smell.

### Always cover the literal special cases

Operators that accept `null()` and `empty()` must include rows for each — see how `test_comparison_eq` in `test_comparison.py` has both `("name", "null()", ...)` and `("name", "empty()", ...)`. Same goes for `true`/`false` on boolean fields, ISO dates/datetimes, and quoted strings (single, double, unquoted).

---

## Test only the public interface

A test must never reach into something prefixed with `_`. That includes `ModelRQLRules._resolve_alias`, `_validate_operator_and_field`, `_validate_ordering`, `_fields`, `_relations`, or `requela._impl`-style modules. Private symbols are implementation details — the whole point of marking them private is reserving the right to change them without breaking callers.

If you feel the urge to test a private function, one of three things is true:
1. **It should be public.** Rename it (drop the underscore) and document it.
2. **Its behavior is observable through a public method.** Test that instead — e.g. test alias resolution by passing the aliased path to `build_query()` and asserting on the resulting SQL.
3. **It's incidental complexity that doesn't need direct coverage.** The public path that uses it covers it.

```python
# Bad: reaches into private state
def test_user_rules_resolves_alias() -> None:
    rules = UserRules()
    assert rules._resolve_alias("events.born.at") == "birth_date"  # don't

# Good: tests the observable contract
def test_valid_aliased_field() -> None:
    """`UserRules` resolves the alias `events.born.at` to `User.birth_date`."""
    stmt = UserRules().build_query("eq(events.born.at,2024-01-01)")
    assert_statements_equal(stmt, select(User).filter(User.birth_date == date(2024, 1, 1)))
```

---

## Type annotations and docstrings (new tests)

CLAUDE.md mandates type annotations on all functions. New tests follow that rule — function parameters and `-> None` return types included. Existing untyped tests are grandfathered; type them as you touch them, but don't open a sweeping retrofit PR.

Common typing notes for ReQueLa:
- Parametrized model parameter: `model: type` is fine (it's an ORM model class).
- SQLAlchemy expected: `expected: Select` from `sqlalchemy.sql.Selectable` is precise; in practice `object` is acceptable in `parametrize` rows.
- Django expected: `expected: QuerySet`.
- The Django `pytest` plumbing doesn't add new fixture types — `tests/conftest.py` calls `django.setup()` at session start, so test functions don't need a fixture parameter for it.

Every new test starts with a one-sentence docstring describing **the rule being enforced**, not what the code does line-by-line:

```python
def test_invalid_operator_for_field() -> None:
    """`UserRules` rejects `eq` on `role` because only `IN`/`OUT` are whitelisted."""
    with pytest.raises(RequelaError, match="Operator 'eq' is not allowed for field 'role'."):
        UserRules().build_query("eq(role,admin)")
```

---

## Fixtures live in `conftest.py`

Fixtures are *never* defined inside test files. The current layout:

```
tests/
├── conftest.py             # session: configures Django + in-memory SQLite
├── test_parser.py          # grammar/transformer (no ORM)
├── sqlalchemy/
│   ├── conftest.py         # SQLAlchemy-only fixtures (add here if/when needed)
│   ├── models.py           # ORM models used as test references (imported directly)
│   ├── rules.py            # ModelRQLRules subclasses (imported directly)
│   ├── utils.py            # assert_statements_equal
│   └── test_*.py
└── django/
    ├── models.py
    ├── rules.py
    ├── utils.py
    └── test_*.py
```

`tests/<backend>/models.py` and `tests/<backend>/rules.py` are **not** fixtures — they're stable reference data imported directly by tests. New shared setup (e.g. a builder factory you want to reuse) goes in `tests/<backend>/conftest.py`.

### Prefer function-scoped fixtures

Default to `scope="function"` (the implicit default). Reach for `module` or `session` scope only when setup is genuinely expensive and the fixture is verifiably immutable across tests. Note that `tests/conftest.py` already configures Django with `:memory:` SQLite at session start — that's the only session-scoped state in the project, and it's a one-shot, not a per-test concern.

### Use `tmp_path` for any filesystem work

ReQueLa shouldn't write files, but if a test ever needs to (e.g. snapshotting documentation output), use the `tmp_path` fixture rather than touching the repo:

```python
from pathlib import Path


def test_documentation_writes_markdown(tmp_path: Path) -> None:
    """`get_documentation()` round-trips through a markdown file unchanged."""
    target = tmp_path / "docs.md"
    target.write_text(UserRules().get_documentation())
    assert target.read_text().splitlines()[0] == "| Field | Operators | Order By |"
```

---

## Test data: use the existing models and rule classes

ReQueLa's test data is the ORM models in `tests/sqlalchemy/models.py` and `tests/django/models.py`, plus the `ModelRQLRules` subclasses in `tests/<backend>/rules.py`. There are **no factories** in this project, and you should not add `factory_boy` or `polyfactory` to test the parser/builders — the inputs are RQL strings and ORM expressions, not constructed domain objects.

When you need a new field shape (e.g. a `Decimal` column with custom precision), extend the existing test models rather than introducing a new fixture file. Mirror the change in both `tests/sqlalchemy/models.py` and `tests/django/models.py`.

### Mixins for shared rules

The rules-layer tests demonstrate that `ModelRQLRules` supports mixin composition — see `TimestampMixin`, `AuditableMixin`, and `NameMixin` in [`tests/sqlalchemy/rules.py`](../../../tests/sqlalchemy/rules.py). Use the same shape when adding rule fixtures for new scenarios; don't define ad-hoc rule classes inline in tests unless the test itself is **about** how an inline class is validated (e.g. `test_filter_class_invalid_operator_for_field`).

---

## Mocking: usually wrong here

ReQueLa is a pure pipeline of input → output. Across the entire test suite there is currently **no mocking**, and that's the right default — there's nothing external to mock, and mocking your own collaborators (parser, transformer, builder) means you're testing the mock, not the code.

If you ever need a mock for a new feature (e.g. a future plugin hook or callback the user provides), use `pytest-mock`'s `mocker` fixture — **not** `unittest.mock` directly. You'd need to add `pytest-mock` to `[dependency-groups].dev` first. Mock at the genuine seam (the user-provided callable), not anything inside `requela`.

```python
from pytest_mock import MockerFixture


def test_hypothetical_custom_callback(mocker: MockerFixture) -> None:
    """A user-supplied callback fires with the resolved field path."""
    callback = mocker.Mock()
    # ... wire callback into the builder, run a query, assert the call
    callback.assert_called_once_with("birth_date")
```

If you find yourself wanting to mock something inside `requela`, stop and refactor the test so it asserts on the public `build_query()` output instead.

---

## Error testing

Use `pytest.raises` with `match=` so you don't accidentally pass on the wrong exception type or message. ReQueLa raises `RequelaError` (and standard exceptions like `ValueError`, `TypeError`, `ExceptionGroup`) from public paths.

```python
def test_invalid_field() -> None:
    """`build_query` raises `RequelaError` for a field not declared on the rules."""
    with pytest.raises(RequelaError):
        UserRules().build_query("eq(email,fail@example.com)")


def test_multiple_validation_errors() -> None:
    """`__init__` raises an `ExceptionGroup` when multiple fields fail validation."""
    class BadRules(ModelRQLRules):
        __model__ = User
        role = FieldRule(allowed_operators=[Operator.LTE, Operator.GTE])
        banana = FieldRule()

    with pytest.raises(ExceptionGroup, match="Model validation failed for 'User'") as exc:
        BadRules()

    assert [(e.__class__, str(e)) for e in exc.value.exceptions] == [
        (ValueError, "Field 'banana' not found in model 'User'."),
        (ValueError, "Invalid operators 'gte', 'lte' for field 'role' of type 'UserRole'."),
    ]
```

The `ExceptionGroup` assertion pattern above is the project's house style — see [`tests/sqlalchemy/test_rules.py`](../../../tests/sqlalchemy/test_rules.py).

---

## Async tests

`pyproject.toml` sets `asyncio_mode = "auto"`, so any `async def test_*` is collected without a decorator. There are no async tests today; if you add one (e.g. for `sqlalchemy[asyncio]` integration), drop the `@pytest.mark.asyncio` decorator entirely:

```python
async def test_async_engine_executes_built_query() -> None:
    """A SQLAlchemy async engine can execute a builder-produced statement."""
    ...
```

---

## Naming

Test names are documentation. Read them like a sentence:

```python
def test_comparison_eq_returns_orm_equality() -> None: ...
def test_valid_aliased_field_resolves_to_model_field() -> None: ...
def test_filter_class_order_field_not_allowed() -> None: ...
def test_tenant_relationship_eq_null() -> None: ...

# Bad — these tell you nothing on a failure report:
def test_eq() -> None: ...
def test_rules() -> None: ...
def test_1() -> None: ...
```

Pattern: `test_<subject>_<verb>_<condition>`. The existing suite leans on `test_<operator>_<scenario>` for builder tests (`test_comparison_eq`, `test_decimal_gte_field`) and `test_<feature>_<scenario>` for rules tests (`test_valid_aliased_field`, `test_filter_class_invalid_operator_for_field`) — follow the local pattern in each file rather than enforcing a single global one.

---

## Coverage

Coverage gate: **≥ 90 %** required, **≥ 95 %** is the goal. The current `pyproject.toml` configures the reports (`--cov=requela --cov-report=term-missing --cov-report=html --cov-report=xml`) but does not set a `fail_under` threshold — that's the project minimum, not a license to drop below 90%.

### Running

```bash
uv run pytest                                        # full suite with coverage (config in pyproject.toml)
uv run pytest tests/sqlalchemy                       # one backend
uv run pytest tests/django                           # the other backend
uv run pytest tests/sqlalchemy/test_comparison.py::test_comparison_eq
uv run pytest -k "alias"                             # filter by name substring
uv run pytest --cov-report=html && open htmlcov/index.html
```

### Closing gaps

When coverage dips, look at `term-missing` output and ask, in order:
1. **Is this branch reachable from a public entry point?** If yes, add an RQL string that exercises it. New branches in `OperatorFunctions` or a builder almost always need new rows in the relevant `@pytest.mark.parametrize`.
2. **Did you forget the other backend?** Most coverage gaps in ReQueLa come from changing one backend and not the other — check both `tests/sqlalchemy/` and `tests/django/`.
3. **Is it dead code?** Delete it.
4. **Is it a defensive `raise` that's genuinely unreachable?** Mark it `# pragma: no cover` (sparingly — `pragma: no cover`, `pragma: no branch`, and `pass` are already excluded by `[tool.coverage.report]`).

Don't chase 100 %. Coverage measures lines executed, not behaviors verified — `branch = true` is already on in `pyproject.toml`, and branch coverage matters more than line coverage.

---

## Mandatory validation before opening a PR

ReQueLa's `CLAUDE.md` requires the full validation suite to pass locally. After adding or changing tests:

```bash
uv run pytest                              # full suite with coverage
uv run ruff check                          # lint (includes flake8-pytest-style)
uv run ruff format --check                 # formatting
uv run mypy src                            # type-check (src only; tests are not gated)
uv run pre-commit run --all-files          # all hooks
```

Don't silence checks, lower coverage thresholds, or skip hooks (`--no-verify`). Fix root causes.

The repo also runs `pytest-randomly` (it's a runtime dependency, surprising as that is) — test order is randomized on every run. If a test only passes in a specific order, **that's a real bug in the test**, not in the runner: a leaked module-level mutation, a shared mutable fixture, or a class attribute being mutated across tests.

---

## Required dev dependencies

`[dependency-groups].dev` in `pyproject.toml` already includes the test stack used by this skill:

```toml
[dependency-groups]
dev = [
    "pytest>=8.3.3,<9.0",
    "pytest-asyncio>=0.24.0,<1.0",
    "pytest-cov>=6.0.0,<7.0",
    # plus: sqlalchemy[asyncio], django, mypy, ruff, pre-commit, ...
]
```

`pytest-randomly` is in the main `dependencies` list. Do not add new runtime testing dependencies casually — CLAUDE.md is explicit that new runtime deps must be justified. New **dev-only** test deps (e.g. `pytest-mock` if a real seam ever appears) belong under `[dependency-groups].dev`.

---
