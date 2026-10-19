---
name: python-testing
description: Write and review high-quality Python tests using pytest. Use whenever creating new tests, refactoring existing tests, debugging test failures, improving coverage, mocking dependencies, mocking HTTP calls, or generating test data — even when the user says "tests" without further detail. Enforces pytest-mock over unittest.mock, mandatory type annotations and docstrings, fixtures kept out of test files (in conftest.py or modules imported by it), factories for test data, pytest-httpx for HTTP mocks, ≥90% coverage (target ≥95%), and testing only public interfaces — never private functions or methods.
---

# Writing Effective Python Tests

This skill defines how tests should be written. Every test must be **atomic**, **self-contained**, **typed**, **documented**, and verify a **single public behavior**. Tests that wander, repeat themselves, or reach into private internals are a maintenance liability — when they break, nobody knows what they were trying to prove.

## Non-negotiables

These rules apply to every test in the project. If you find yourself wanting to break one, that's a signal the design is off, not the rule.

1. **Use `pytest-mock` (the `mocker` fixture), never `unittest.mock` directly.**
2. **Fixtures live in `conftest.py`** or in modules that `conftest.py` imports. They never live inside test files.
3. **Type annotations are mandatory** on every test function, fixture, and helper — including return types (`-> None` for tests).
4. **Use factories** to generate test data. Don't sprinkle bespoke dicts and constructors across test files.
5. **Use `pytest-httpx`** to mock HTTP calls. Never patch `requests`/`httpx` directly.
6. **Coverage must be ≥ 90 %**, target ≥ 95 %. CI gates on the lower bound.
7. **Every test has a docstring** stating the behavior under test in one sentence.
8. **Test only public interfaces.** Never call into `_private` functions, methods, or modules.

The rest of this skill explains how to satisfy each rule and gives the standard patterns to reach for.

---

## Test structure

### One behavior per test

Each test verifies a single behavior. The test name and docstring should tell you exactly what's broken when it fails. Multiple `assert` statements are fine when they all examine the same behavior.

```python
def test_user_creation_sets_default_role() -> None:
    """A freshly created `User` defaults to the 'member' role."""
    user = User(name="Alice")
    assert user.role == "member"
    assert user.id is not None
    assert user.created_at is not None
```

If a test name uses "and" — `test_create_user_and_promote_them` — split it.

### Parameterize variations of the same concept

Use `pytest.mark.parametrize` for inputs that exercise the *same* logic. Don't smuggle different behaviors into one parameterized test.

```python
import pytest

@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ("hello", "HELLO"),
        ("World", "WORLD"),
        ("", ""),
        ("123", "123"),
    ],
)
def test_uppercase_conversion(input_str: str, expected: str) -> None:
    """`str.upper()` returns the uppercase form for any string input."""
    assert input_str.upper() == expected
```

### Separate tests for distinct behaviors

If two cases would need different setup, different mocks, or different docstrings, write two tests. Parameterizing them only saves a few lines and obscures intent.

---

## Type annotations (mandatory)

Every test function, every fixture, every helper. Return types included. Tests are code; the same `mypy --strict` (or equivalent) standard you'd hold production code to applies here.

```python
import pytest
from pytest_mock import MockerFixture

def test_compute_total_returns_sum() -> None:
    """`compute_total` sums the `amount` field across line items."""
    items = [LineItem(amount=10), LineItem(amount=5)]
    assert compute_total(items) == 15

@pytest.fixture
def order(user: User) -> Order:
    """An `Order` placed by the default user, with no items yet."""
    return Order(user=user)

def test_uses_mocker(mocker: MockerFixture) -> None:
    """Demonstrates the required typing for the `mocker` fixture."""
    ...
```

Common typing imports:
- `pytest_mock.MockerFixture` — the `mocker` fixture parameter.
- `pytest_httpx.HTTPXMock` — the `httpx_mock` fixture parameter.
- `pathlib.Path` — for `tmp_path`.
- `pytest.MonkeyPatch`, `pytest.FixtureRequest`, `pytest.LogCaptureFixture`, `pytest.CaptureFixture` as applicable.

---

## Docstrings (mandatory)

Every test starts with a one-sentence docstring describing the behavior under test. The docstring is what shows up in a failure report and what a teammate reads when triaging at 3 AM.

```python
def test_login_rejects_unknown_user() -> None:
    """`login()` raises `AuthError` when the username does not exist."""
    ...

def test_cart_total_excludes_removed_items() -> None:
    """Items removed via `Cart.remove()` are excluded from `Cart.total`."""
    ...
```

A good docstring states *the rule being enforced*, not what the test code does line-by-line. "Calls login then asserts" is useless; "raises `AuthError` when the username does not exist" is the contract.

---

## Test only the public interface

A test must never reach into something prefixed with `_`. That includes `_private_helper()`, `MyClass._internal_state`, and `myproject._impl` modules. Private symbols are implementation details — the whole point of marking them private is reserving the right to change them without breaking callers, including tests.

If you feel the urge to test a private function, one of three things is true:
1. **It should be public.** Rename it (drop the underscore) and document it.
2. **Its behavior is observable through a public method.** Test that instead.
3. **It's incidental complexity that doesn't need direct coverage.** The public path that uses it covers it.

```python
# Bad: reaches into private state
def test_cache_internal_dict_grows() -> None:
    cache = Cache()
    cache.set("k", "v")
    assert "k" in cache._store  # don't

# Good: tests the observable contract
def test_cache_returns_stored_value() -> None:
    """`Cache.get()` returns the value previously set under the same key."""
    cache = Cache()
    cache.set("k", "v")
    assert cache.get("k") == "v"
```

The same rule applies to mocking: don't `mocker.patch("myproject.module._helper")`. If `_helper` matters to a test, the seam is in the wrong place — refactor or test through the public path.

**Autouse fixtures are the one place a leading underscore is expected.** A fixture whose return value is never consumed is conventionally named with a leading underscore (e.g. `_reset_cache`) to signal "side-effect only" — that's a pytest idiom, not a private product symbol. Defining and registering such fixtures is fine; importing or calling one by name from a test body is not.

---

## Fixtures live in `conftest.py`

Fixtures are *never* defined inside test files. They live in `conftest.py` (one per test directory), or in plain Python modules that `conftest.py` imports. This keeps test files focused on assertions and lets fixtures be reused across the suite without circular weirdness.

### Prefer function-scoped fixtures

Default to `scope="function"` (the implicit default). Reach for `module` or `session` scope only when setup is genuinely expensive (containers, large data) and the fixture is verifiably immutable across tests. A shared mutable fixture that "should be fine" is the source of every flaky test you've ever debugged.

### Use `tmp_path` for filesystem work

```python
from pathlib import Path

def test_writes_config_file(tmp_path: Path) -> None:
    """`save_config()` writes the rendered TOML to the given path."""
    target = tmp_path / "config.toml"
    save_config(target, {"key": "value"})
    assert target.read_text().strip() == 'key = "value"'
```

---

## Factories for test data

Don't construct objects with raw dicts or repeated `User(name="Alice", email="a@b.c", ...)` boilerplate scattered across files. Define each kind of test object in **one** place that builds a valid instance with sensible defaults and lets a test override only the fields it cares about. That single source of truth is a "factory", however you implement it.

A factory is a *pattern*, not a particular library. Use whatever matches the project's existing conventions — don't add a new dependency just to satisfy this rule, and don't mix several approaches in one suite. Common implementations, in rough order of how much machinery they add:

- **Factory fixtures** — a `conftest.py` fixture returns a builder callable. No extra dependencies, works for sync or async construction (e.g. persisting an ORM row), and composes naturally with other fixtures. Often the simplest choice, and the default when the codebase already does this.
- **`factory_boy`** — a declarative class per model, with sequences, sub-factories, and traits. A good fit once you have many related models.
- **`polyfactory`** — derives factories automatically from Pydantic models or dataclasses; handy for schema-heavy projects.

**Scope:** the factory rule applies to **in-memory object construction** — domain models, DTOs, ORM rows. It does **not** apply to fixture documents that represent external inputs (OpenAPI specs, sample JSON/YAML payloads, golden files). Those belong under `tests/fixtures/` as static files and are loaded as-is — wrapping them in a factory adds noise without value.

### Factory fixtures (no extra dependencies)

A fixture that returns a builder keeps construction in `conftest.py` and lets each test override just what matters:

```python
# conftest.py
from collections.abc import Callable

import pytest

from myproject.models import User

@pytest.fixture
def user_factory() -> Callable[..., User]:
    """Build a `User` with overridable defaults."""
    def _build(*, name: str = "Alice", role: str = "member", **kwargs: object) -> User:
        return User(name=name, role=role, **kwargs)

    return _build
```

```python
def test_admin_can_cancel_any_order(user_factory: Callable[..., User]) -> None:
    """An `admin` user may cancel orders belonging to other users."""
    admin = user_factory(role="admin")
    ...
```

The same shape works for objects that need I/O to create — e.g. an async fixture whose builder inserts a row and returns the persisted model. That `role="admin"` makes the *thing being tested* obvious; everything else is noise the factory handles.

### factory_boy

```python
# tests/factories.py
import factory
from myproject.models import Order, User

class UserFactory(factory.Factory):
    class Meta:
        model = User

    name = factory.Sequence(lambda n: f"user-{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.name}@example.com")
    role = "member"

class OrderFactory(factory.Factory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    total = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
```

```python
def test_admin_can_cancel_any_order() -> None:
    """An `admin` user may cancel orders belonging to other users."""
    admin = UserFactory(role="admin")
    other_order = OrderFactory()  # belongs to a different user
    cancel_order(admin, other_order)
    assert other_order.status == "cancelled"
```

### polyfactory (for Pydantic models)

```python
from polyfactory.factories.pydantic_factory import ModelFactory
from myproject.schemas import UserCreate

class UserCreateFactory(ModelFactory[UserCreate]):
    __model__ = UserCreate
```

```python
def test_create_user_endpoint_accepts_valid_payload(client: TestClient) -> None:
    """`POST /users` returns 201 for a payload satisfying the `UserCreate` schema."""
    payload = UserCreateFactory.build().model_dump()
    response = client.post("/users", json=payload)
    assert response.status_code == 201
```

Library-based factories live in `tests/factories.py` (or a `tests/factories/` package for larger suites) and are imported by tests directly or wired into fixtures; factory fixtures live in `conftest.py` like any other fixture.

---

## Mocking with `pytest-mock`

Use the `mocker` fixture for every mock. Never `from unittest.mock import patch` in a test. The `mocker` fixture cleans up automatically after the test, gives you a single consistent API, and makes the test signature self-documenting.

```python
from pytest_mock import MockerFixture

def test_send_notification_calls_email_service(mocker: MockerFixture) -> None:
    """`send_notification()` delegates delivery to `email_service.send`."""
    send_mock = mocker.patch("myproject.notifications.email_service.send")
    send_notification(user_id=1, message="hi")
    send_mock.assert_called_once_with(to=1, body="hi")
```

### Mock at the boundary, not your own code

Mock external systems (HTTP, message queues, third-party SDKs, the clock, the filesystem) — not the classes and functions you wrote. If your test of `OrderService` mocks `OrderRepository`, you're testing your mock setup, not your code.

```python
# Bad: mocking your own collaborator
def test_order_service_creates_order(mocker: MockerFixture) -> None:
    repo = mocker.MagicMock()
    service = OrderService(repo)
    service.create(user_id=1, total=Decimal("10.00"))
    repo.save.assert_called_once()  # passes whether the code is right or wrong

# Good: real collaborator, in-memory backend
def test_order_service_persists_created_order(repository: InMemoryOrderRepo) -> None:
    """`OrderService.create()` persists the new order to the repository."""
    service = OrderService(repository)
    service.create(user_id=1, total=Decimal("10.00"))
    assert len(repository.all()) == 1
```

### Async mocks

```python
async def test_async_external_call(mocker: MockerFixture) -> None:
    """`fetch_user()` returns the data from the external client."""
    mocker.patch(
        "myproject.users.external_client.fetch",
        new_callable=mocker.AsyncMock,
        return_value={"id": 1, "name": "Alice"},
    )
    result = await fetch_user(1)
    assert result == {"id": 1, "name": "Alice"}
```

### Spying without replacing

When you want to assert something was called but still let it run:

```python
def test_logs_on_save(mocker: MockerFixture, repository: InMemoryOrderRepo) -> None:
    """`Order.save()` emits an info log with the order id."""
    log_spy = mocker.spy(myproject.orders, "logger")
    order = OrderFactory()
    order.save(repository)
    log_spy.info.assert_called_once()
```

---

## HTTP mocking with `pytest-httpx`

Never patch `httpx.Client.send` or `requests.get` by hand. The `httpx_mock` fixture (from `pytest-httpx`) is the supported tool — it works for sync and async, supports streaming responses, and verifies that every registered response was actually called.

```python
import pytest
from pytest_httpx import HTTPXMock

def test_fetch_weather_parses_response(httpx_mock: HTTPXMock) -> None:
    """`fetch_weather()` returns the temperature parsed from the JSON body."""
    httpx_mock.add_response(
        url="https://api.weather.example/v1/now?city=London",
        json={"temp_c": 14.2},
    )
    assert fetch_weather("London") == 14.2

def test_fetch_weather_raises_on_5xx(httpx_mock: HTTPXMock) -> None:
    """`fetch_weather()` raises `WeatherUnavailable` on a 5xx response."""
    httpx_mock.add_response(
        url="https://api.weather.example/v1/now?city=London",
        status_code=503,
    )
    with pytest.raises(WeatherUnavailable):
        fetch_weather("London")

async def test_async_client_retries_on_timeout(httpx_mock: HTTPXMock) -> None:
    """The async client retries once on a timeout, then succeeds."""
    httpx_mock.add_exception(httpx.TimeoutException("slow"))
    httpx_mock.add_response(json={"ok": True})
    result = await async_fetch()
    assert result == {"ok": True}
```

`pytest-httpx` fails the test if a registered response is never matched, which catches dead test setup. To allow unmatched responses (rarely needed), pass `assert_all_responses_were_requested=False` to a per-test marker.

### Assert the request through matchers, not by fetching it back

Register what the request must look like on `add_response` itself, using the built-in matchers. **Do not** pull the request out afterwards with `httpx_mock.get_request()` / `get_requests()` and then assert on `.url`, `.headers`, `.content`, or a parsed body. Because `pytest-httpx` fails the test when no registered response matches, a matcher on `add_response` *is* the assertion — and it's stronger: `get_request()` raises `AssertionError` the moment a second request is made, so hand-rolled `_last_request`-style helpers silently break as soon as the code under test makes more than one call.

Match with these `add_response`/`add_exception` keywords:

- `url=` — full URL **including query string**; query params are compared order-independently.
- `method=` — the HTTP verb.
- `match_json=` — the request body, JSON-decoded and compared structurally.
- `match_headers=` — a dict of headers the request must carry (subset match).
- `match_params=` — query params as a dict, when you'd rather not inline them in `url`.
- `match_content=` / `match_data=` / `match_files=` — raw bytes, form data, multipart files.

```python
# Bad: fetch the request back and assert on it. Breaks on a second request,
# and needs a helper that re-implements what the matchers already do.
def _last_request(httpx_mock: HTTPXMock) -> httpx.Request:
    request = httpx_mock.get_request()
    assert request is not None
    return request

async def test_create_posts_payload(client: ApiClient, httpx_mock: HTTPXMock) -> None:
    """`create` POSTs the payload to the resource URL."""
    httpx_mock.add_response(method="POST", json={"id": "OBJ-1"})
    await client.create("billing/journals", {"name": "j"})
    assert _last_request(httpx_mock).url.path.endswith("billing/journals")  # don't
    assert json.loads(_last_request(httpx_mock).content) == {"name": "j"}   # don't

# Good: the matchers ARE the assertion — the test fails if the request doesn't match.
async def test_create_posts_payload(client: ApiClient, httpx_mock: HTTPXMock) -> None:
    """`create` POSTs the payload to the resource URL."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.example/v1/billing/journals",
        match_json={"name": "j"},
        json={"id": "OBJ-1"},
    )
    result = await client.create("billing/journals", {"name": "j"})
    assert result == {"id": "OBJ-1"}
```

**The one legitimate use of `get_requests()`** is asserting *emergent, cross-request* behavior that no single matcher can express: how many requests were made (retry counts, pacing), how a payload was split across a runtime-determined number of requests (chunking/pagination distribution), or a wire-format property of the serialized body (e.g. compact JSON has no `", "` separators). Verifying that *one* request had the right URL / body / params / headers is never one of those cases — use matchers.

For codebases on `requests`, prefer migrating to `httpx` so you can use `pytest-httpx` everywhere; if that's not feasible, use `respx` (httpx) or `pytest-httpserver`. Pick one tool for the project and stick with it — don't mix.

The "don't mix" rule is about **mocking** libraries. A tool that serves *real* HTTP for a test (e.g. `pytest-httpserver`) operates at a different layer and may coexist with a mocking tool — for example, mocking an upstream API while serving local fixture documents over HTTP to exercise a loader end-to-end.

---

## Coverage

Coverage gate: **≥ 90 %** required, **≥ 95 %** is the goal. Aim higher than the gate so a few lines of churn don't break CI.

### Configuration

```toml
# pyproject.toml
[tool.coverage.run]
branch = true
source = ["myproject"]
omit = ["myproject/__main__.py", "myproject/_version.py"]

[tool.coverage.report]
fail_under = 90
show_missing = true
skip_covered = false
exclude_also = [
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@overload",
    "\\.\\.\\.",
]
```

### Running

```bash
uv run pytest --cov=myproject --cov-report=term-missing
uv run pytest --cov=myproject --cov-report=html        # browse htmlcov/index.html
uv run pytest --cov=myproject --cov-fail-under=90
```

### Closing gaps

When coverage dips, look at `term-missing` output and ask, in order:
1. **Is this branch reachable from a public entry point?** If yes, write a test that exercises it.
2. **Is it dead code?** Delete it.
3. **Is it a defensive `raise` that's genuinely unreachable?** Mark it: `# pragma: no cover` (sparingly).

Don't chase 100 %. Coverage measures lines executed, not behaviors verified — a poorly-asserted test can hit every line and prove nothing. Branch coverage matters more than line coverage; `branch = true` in the config above turns it on.

---

## Naming

Test names are documentation. Read them like a sentence:

```python
def test_login_fails_with_invalid_password() -> None: ...
def test_user_can_update_own_profile() -> None: ...
def test_admin_can_delete_any_user() -> None: ...
def test_cart_total_excludes_removed_items() -> None: ...

# Bad — these tell you nothing on a failure report:
def test_login() -> None: ...
def test_update() -> None: ...
def test_1() -> None: ...
```

Pattern: `test_<subject>_<verb>_<condition>`.

---

## Error testing

```python
def test_calculate_rejects_negative_input() -> None:
    """`calculate()` raises `ValueError` when input is negative."""
    with pytest.raises(ValueError, match="must be positive"):
        calculate(-1)

async def test_connect_raises_on_invalid_host() -> None:
    """`connect()` raises `ConnectionError` for an unreachable host."""
    with pytest.raises(ConnectionError):
        await connect("invalid.host.invalid")
```

Always include `match=` on `pytest.raises` so you don't accidentally pass on the wrong exception type or message.

---

## Async tests

If the project sets `asyncio_mode = "auto"` (in `pyproject.toml` under `[tool.pytest.ini_options]`), drop the decorator:

```python
async def test_async_operation() -> None:
    """`some_async_function()` resolves to the expected value."""
    result = await some_async_function()
    assert result == expected
```

If `asyncio_mode` is not set, mark the test:

```python
@pytest.mark.asyncio
async def test_async_operation() -> None: ...
```

Check `pyproject.toml` first to know which form applies to the codebase.

---

## Running tests

```bash
uv run pytest -n auto                       # parallel, all cores (pytest-xdist)
uv run pytest -n auto -x                    # stop on first failure
uv run pytest tests/unit/test_pricing.py    # specific file
uv run pytest -k "cancel"                   # match by name substring
uv run pytest -m "not slow"                 # exclude markers
uv run pytest --lf                          # rerun last-failed
uv run pytest -vv --tb=short                # verbose, concise tracebacks
```

---

## Required dev dependencies

Make sure `pyproject.toml` lists these in the test/dev group:

```toml
[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio",
    "pytest-cov",
    "pytest-mock",
    "pytest-httpx",
    "pytest-xdist",       # parallel runs
    # Optional: only if you use a factory library. Factory fixtures
    # (a conftest fixture returning a builder) need no dependency.
    "factory-boy",        # or "polyfactory" for Pydantic-heavy work
]
```

---

## Checklist before considering the job done

- [ ] Each test verifies one behavior; name and docstring describe it.
- [ ] Every test, fixture, and helper has type annotations including return type.
- [ ] Every test has a one-sentence docstring stating the behavior under test.
- [ ] No test reaches into `_private` symbols (functions, methods, modules, attributes).
- [ ] Fixtures live in `conftest.py` or modules imported by it — never in the test file.
- [ ] Mocks use `mocker` (pytest-mock); no direct `unittest.mock.patch`.
- [ ] HTTP mocks use `httpx_mock` (pytest-httpx); no hand-patched `requests`/`httpx`.
- [ ] HTTP requests are asserted via `add_response` matchers (`url`, `method`, `match_json`, `match_headers`, `match_params`), not by fetching the request back with `get_request()`/`get_requests()` — the latter is reserved for cross-request behavior (counts, chunking distribution, wire format).
- [ ] Test data comes from factories, not bespoke dicts or repeated constructor calls.
- [ ] `pytest.raises` calls include `match=`.
- [ ] Coverage ≥ 90 % on the changed module (target 95 %); branch coverage on.
- [ ] No stray `print`, `breakpoint`, or commented-out code.
