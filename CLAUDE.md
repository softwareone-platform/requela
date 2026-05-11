# ReQueLa Development Guidelines

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ReQueLa parses RQL (Resource Query Language) expressions and translates them into ORM queries for either **SQLAlchemy** or **Django**. The public entry points are `get_builder_for_model(model)` for direct use, and `ModelRQLRules` subclasses for a declarative whitelist of fields/operators/aliases.

The pipeline is **RQL string → Lark AST → backend-specific query object**, with a small number of seams where backends and rule sets plug in. The two-layer split (backend-agnostic transformer + per-backend builders) is what allows the same parsed expression tree to drive either SQLAlchemy or Django without duplicating grammar logic.

## Requirements and Design Authority

The supported RQL operators, syntax, and end-user examples live in [`README.md`](README.md) — it is the source of truth for the public RQL contract. Consult it before changing grammar or operator semantics; any user-visible change to grammar, operators, or builder behavior must be reflected there in the same PR.

## Project Structure

```
.
├── src/requela/
│   ├── grammar.lark        # RQL grammar (Lark)
│   ├── parser.py           # Lark parser wrapper
│   ├── transformer.py      # Backend-agnostic AST → expression dataclasses
│   ├── dataclasses.py      # FilterExpression, OrderByExpression, DEFAULT_OPERATORS, OperatorFunctions
│   ├── rules.py            # ModelRQLRules, FieldRule, RelationshipRule — declarative whitelist layer
│   ├── exceptions.py
│   └── builders/
│       ├── __init__.py     # get_builder_for_model() dispatch
│       ├── base.py         # Abstract QueryBuilder
│       ├── sqlalchemy.py   # SQLAlchemy backend
│       └── django.py       # Django backend
├── tests/
│   ├── conftest.py         # Calls django.setup() with in-memory SQLite
│   ├── test_parser.py      # Grammar/transformer layer, no ORM
│   ├── sqlalchemy/         # SQLAlchemy backend suite
│   └── django/             # Django backend suite (parallel files)
├── docs/                   # Roadmap and supplementary docs
├── pyproject.toml          # Dependencies and tool configuration
├── .python-version         # Python 3.12
├── docker-compose.yaml     # Containerised test runner
└── README.md               # Public RQL grammar and usage reference
```

## Commands

The project uses **uv** for dependency management and **pytest** for tests. CI and the devcontainer both rely on `uv sync`.

- Install deps: `uv sync` (uses `uv.lock`; `--frozen` in CI)
- Run all tests with coverage: `uv run pytest` (config in `pyproject.toml` already adds `--cov=requela --cov-report=...`)
- Run a single test: `uv run pytest tests/sqlalchemy/test_comparison.py::test_eq` or `uv run pytest -k <expr>`
- Run only one backend's suite: `uv run pytest tests/sqlalchemy` or `uv run pytest tests/django`
- Lint / format: `uv run ruff check` and `uv run ruff format` (line length 100, target py3.12)
- Type-check: `uv run mypy src`
- Pre-commit: `uv run pre-commit run --all-files` (ruff + ruff-format + whitespace hooks)
- Docker test run: `docker compose run --rm tests`

Python 3.12 is required (`.python-version`, `requires-python = ">=3.12,<4"`).

## Mandatory Validation Checks

Every change must pass locally and in CI:

```bash
uv run pytest                             # Full suite with coverage
uv run ruff check                         # Lint
uv run ruff format --check               # Formatting
uv run mypy src                           # Type-check
uv run pre-commit run --all-files         # All pre-commit hooks
```

Do not silence checks, lower coverage thresholds, or disable hooks; fix root causes instead.

## Per-Change Workflow

1. Implement one logical change at a time.
2. Add new tests for features; regression tests for bug fixes.
3. When changing shared behavior, update **both** `tests/sqlalchemy/` and `tests/django/` — they are deliberately parallel.
4. Update `README.md` for any user-visible change to grammar, operators, or builder behavior in the same PR.
5. Run the full validation suite locally before opening a PR.

## Git Practices

* `main` is protected; all changes require a PR.
* Branch naming: `<type>/<slug>` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`). Internal tickets may prefix with the tracker key (e.g. `MPT-11328-...`) to match existing history.
* Commits follow [Conventional Commits](https://www.conventionalcommits.org/) format.
* Imperative subject lines ≤72 characters; body explains *why*, not *what*.
* One logical change per commit; rebase before requesting review.
* Never force-push to `main`; never bypass hooks (`--no-verify`) or signing without explicit reason.

## Coding Standards

### Core Principles
* Follow PEP 20 (The Zen of Python).
* Type annotations are mandatory on all functions and parameters; `mypy src` must pass.
* Public interface precedes private implementation in a module.
* Self-explanatory code; comments surface non-obvious *why* only.
* Keep the transformer backend-agnostic — backend specifics belong in `builders/`.

### Import Rules
* Top-of-file placement only; no inline imports.
* Avoid aliases unless name conflicts require them.
* Refactor to eliminate circular imports; no lazy imports.

### Module Organization
1. Imports
2. Constants
3. Public interface
4. Private implementation

### Function & Class Organization
1. Public members
2. Private members

### Documentation
* Every public symbol requires a docstring.
* Document return values and exceptions, not obvious implementation details.
* Self-contained docstrings; no cross-file references.
* Respect the 100-character line length (`ruff` enforces this).

## Third-Party Dependencies

New runtime dependencies must be:
* Actively maintained with recent releases.
* Licensed under OSI-approved licenses compatible with Apache-2.0 (the project license).
* Justified in the PR description — ReQueLa's runtime surface is intentionally small (`lark` is the only non-test runtime dep). Prefer the standard library or an existing dep before adding a new one.

Dev-only dependencies belong under `[dependency-groups].dev` in `pyproject.toml`.

## Architecture

### Parse → transform → apply

1. `src/requela/grammar.lark` defines the RQL grammar (filters, `order_by`, `any`, literals including `null()`/`empty()`, UUID/date/datetime terminals).
2. `parser.py` builds a Lark parser from that grammar; `parse()` returns the AST.
3. `transformer.py` (`RQLTransformer`) walks the AST. It is **backend-agnostic**: each grammar rule (`and_op`, `eq_op`, `any_expression`, `order_expression`, ...) is mapped to a callable from an `OperatorFunctions` dataclass injected at construction time. Output is a list of `FilterExpression` / `OrderByExpression` dataclasses (see `dataclasses.py`).
4. `builders/base.py` (`QueryBuilder`, abstract) wires its own `apply_and`/`apply_eq`/`apply_any`/... methods into an `OperatorFunctions` and passes that to the transformer. `build_query()` iterates the resulting expressions, calling `apply_filter` and `apply_order_by`, then finishes with `apply_joins`.
5. Concrete backends live in `builders/sqlalchemy.py` and `builders/django.py`. `builders/__init__.get_builder_for_model()` dispatches by duck-typing: `__table__` → SQLAlchemy, `_meta` → Django.

When adding a new operator, you must touch four places: the grammar, the transformer (route the new rule), `OperatorFunctions`, and **both** backend builders (`apply_<op>` plus a default operator set in `DEFAULT_OPERATORS` if it's type-sensitive).

### Rules layer (`rules.py`)

`ModelRQLRules` is the declarative surface most users interact with. Each subclass sets `__model__` and exposes `FieldRule` / `RelationshipRule` attributes. `__init_subclass__` collects them into `_fields` / `_relations` class dicts (so mixins like `TimestampMixin` in `tests/sqlalchemy/rules.py` work).

On `__init__`, `_validate()` introspects the model via the builder's `get_field_type()` and:
- Infers default operators per field type from `DEFAULT_OPERATORS` (`dataclasses.py`) when `allowed_operators` is not set.
- Rejects operators incompatible with the field's Python type, raising `ExceptionGroup`.

The rules instance then exposes three classmethods to the builder as callbacks:
- `_resolve_alias` — maps RQL aliases like `events.created.at` back to real model field paths.
- `_validate_operator_and_field` — runtime guard during query building.
- `_validate_ordering` — enforces `allow_ordering=False`.

This is the only place where alias resolution happens; **the builders themselves do not know about aliases** — they receive resolved field paths via the callbacks.

### Tests

Tests are split by backend under `tests/sqlalchemy/` and `tests/django/`, with parallel files (`test_comparison.py`, `test_logical.py`, `test_ordering.py`, `test_relationship.py`, `test_rules.py`). When changing shared behavior, update **both** suites.

`tests/conftest.py` calls `django.setup()` at session start with an in-memory SQLite config — no external services are needed. `tests/test_parser.py` covers the grammar/transformer layer directly without either ORM.
