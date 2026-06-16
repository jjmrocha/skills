# Python Unit Test Reference — pytest

Prescriptive guide for writing Python unit tests with **pytest**. Following it produces tests that read consistently and follow the universal principles in `SKILL.md`.

**Stack**: pytest • `pytest.mark.parametrize` • `monkeypatch` / `unittest.mock` • plain `assert` statements.

> **Always check the project's existing tests first.** If the project uses `unittest.TestCase` classes, follow that style instead of pytest's functional style. If it uses `pytest-mock`, prefer `mocker` over `unittest.mock.patch`. The reference is the default for greenfield code.

This reference follows the **FIRST-U** principles (Fast, Isolated, Repeatable, Self-validating, Timely, Understandable) defined in §4 of the main skill. Every test here should satisfy each letter.

---

## 1. Tooling

- **pytest** as the runner.
- **plain `assert`** statements — pytest rewrites them to produce diff output. Do not use `unittest`'s `self.assertEqual` style.
- **`monkeypatch`** (pytest's built-in fixture) for setting/clearing environment variables, attributes, dict entries, and replacing module-level functions during a test.
- **`unittest.mock.patch`** / **`MagicMock`** for object-level mocks. If `pytest-mock` is installed, prefer `mocker` (its lifecycle is tied to the test automatically).
- **`pytest.raises`** for exception assertions.
- **`pytest.mark.parametrize`** for table-driven tests.
- **`pytest.fixture`** for reusable setup. Module-scoped fixtures only when the setup is truly immutable.

If the project uses `pytest-asyncio` or `anyio`, follow its conventions for `async def` tests.

---

## 2. File layout

- Tests live under a top-level `tests/` directory (or `test/`) that mirrors the package structure:

  ```
  src/myapp/orders/service.py
  tests/orders/test_service.py
  ```

  If the project uses inline tests under the package (`src/myapp/orders/test_service.py`), follow that.

- One test module per production module. File name: **`test_<module>.py`**.
- Test functions are top-level. Use a class **only** to group fixtures with related tests (`class TestOrderService:`); never as a way to organize unrelated tests.

---

## 3. What to test, by layer

| Layer | Mock | Don't mock | Focus |
|-------|------|------------|-------|
| **Views / handlers** | Service layer | — | Input validation, auth, response shape |
| **Services / use cases** | Repository interface | Internal pure functions | Business logic: given state + inputs, verify outputs |
| **Pure functions / transformers** | Nothing | Everything | Input → output mapping. `@pytest.mark.parametrize`. |
| **External clients** | `responses` / `httpx.MockTransport` — not the SDK directly | — | Request shape (method, URL, headers) and every response branch |
| **Event consumers** | Message queue mock | — | Payload schema, duplicate handling |

---

## 4. Test function naming

Format: **`test_<function>_<scenario>_<expected>`**, snake_case, describing the unit, the condition, and the outcome.

```python
def test_withdraw_insufficient_balance_raises_overdraft_error(): ...
def test_parse_date_invalid_format_returns_none(): ...
def test_create_order_valid_cart_persists_order_and_sends_email(): ...
def test_hash_password_empty_input_raises_value_error(): ...
```

Rules:
- All lowercase, snake_case. No camelCase, no `should_`/`it_` prefixes.
- The name describes the input/state condition and the expected outcome.
- For factories or trivial happy paths, `test_<function>` alone is acceptable (`test_default_config`).
- Avoid `test_1`, `test_simple`, `test_works`.

When using a class to group tests for one production class, the class is `Test<ClassUnderTest>` and methods follow the same naming, dropping the leading `test_` from the class but keeping it on methods:

```python
class TestOrderService:
    def test_create_order_valid_cart_persists_order(self): ...
    def test_create_order_zero_total_raises_validation_error(self): ...
```

---

## 5. Canonical variable names

| Variable           | Meaning                                                            |
|--------------------|--------------------------------------------------------------------|
| `class_under_test` | The instance whose behavior is being tested. Use this for non-trivial objects. For free functions or where the type is obvious, a short domain name (`service`, `parser`) is also acceptable. |
| `result`           | The return value of the function under test.                       |
| `expected`         | The expected value, when it needs a named variable.                |
| `mock_<thing>`     | A mock for an external collaborator (`mock_repository`, `mock_clock`). |

Use **the same parameter names** as the function under test for inputs — the connection between test setup and the call should be obvious.

---

## 6. Given / When / Then structure

Use lowercase block comments to delimit phases — `# given`, `# when`, `# then` — **only if the existing project tests already use them**. If they don't, keep the same three-block structure without comments:

```python
def test_parse_date_iso_format_returns_date():
    # given
    class_under_test = DateParser()
    input = "2024-03-15"
    # when
    result = class_under_test.parse(input)
    # then
    assert result == date(2024, 3, 15)
```

Rules:
- Always lowercase: `# given`, `# when`, `# then`. No colons.
- The `# when` block is **one statement** — the call under test.
- All assertions live under `# then`.
- Omit `# given` when a fixture supplies all setup.
- For functions that return `None` and act via side effects, `# when` calls the function and `# then` inspects the resulting state.

---

## 7. Assertions — plain `assert`

pytest rewrites `assert` to produce rich diffs. Use it for everything:

```python
assert result == expected
assert result is None
assert result is not None
assert flag is True
assert items == ["a", "b", "c"]
assert "substring" in message
assert len(items) == 3
assert item in collection
```

### Floating point

```python
from pytest import approx
assert result == approx(0.1 + 0.2)
assert position == approx((1.0, 2.0), rel=1e-3)
```

### Unordered collections

```python
assert sorted(result) == sorted(expected)
# or, when items are hashable:
assert set(result) == set(expected)
```

### Custom assertion messages

Add a message only when the assertion alone is unclear:

```python
assert order.status == Status.PAID, f"order {order.id} should be PAID after capture"
```

Default to no message — pytest's diff is usually enough.

---

## 8. Exception testing — `pytest.raises`

```python
def test_withdraw_insufficient_balance_raises_overdraft_error():
    # given
    class_under_test = Account(balance=Decimal("50"))
    # when / then
    with pytest.raises(OverdraftError, match="Withdrawal exceeds balance"):
        class_under_test.withdraw(Decimal("100"))
```

Rules:
- Use `match=` for a regex substring check on the exception message. Don't use a separate `assert str(exc) == ...` for substrings.
- For exact-message assertions, capture the exception via `excinfo`:

```python
with pytest.raises(OverdraftError) as excinfo:
    class_under_test.withdraw(Decimal("100"))
assert str(excinfo.value) == "Withdrawal exceeds balance."
```

- Combine `# when` and `# then` into a single block when the action and the assertion are inseparable (as in `pytest.raises`).

---

## 9. Fixtures

Use `@pytest.fixture` for reusable setup. Default to **function scope** — the cost of recreating state is almost always preferable to the risk of leaks between tests.

```python
@pytest.fixture
def order_repository():
    return InMemoryOrderRepository()


@pytest.fixture
def class_under_test(order_repository):
    return OrderService(order_repository)
```

Rules:
- Fixtures live in `conftest.py` when shared across multiple test files. Module-local fixtures live at the top of the test file.
- Yield-based fixtures for setup/teardown:

  ```python
  @pytest.fixture
  def temp_db_file(tmp_path):
      path = tmp_path / "data.db"
      path.touch()
      yield path
      # cleanup happens after yield, but tmp_path already handles it
  ```

- Prefer pytest's built-in fixtures (`tmp_path`, `monkeypatch`, `capsys`, `caplog`) over hand-rolled equivalents.
- `scope="module"` or `scope="session"` only when setup is genuinely expensive **and** demonstrably immutable. The wrong choice causes flakes.

---

## 10. Parameterized tests

Use `@pytest.mark.parametrize` for table-driven scenarios. **Always include `ids=`** so test IDs read clearly in pytest output.

```python
@pytest.mark.parametrize(
    "input, expected",
    [
        ("get", HttpMethod.GET),
        ("GET", HttpMethod.GET),
        ("post", HttpMethod.POST),
        ("invalid", None),
    ],
    ids=["lowercase_get", "uppercase_get", "lowercase_post", "unknown_value_returns_none"],
)
def test_from_string(input, expected):
    # when
    result = HttpMethod.from_string(input)
    # then
    assert result == expected
```

Rules:
- Parameter names match the function-under-test's parameter names where possible.
- `ids` are snake_case sentences describing each row. **Never let pytest auto-generate IDs** for non-trivial cases — they become unreadable.
- For multi-parameter cases, list arguments in `ids` in the same order as cases.

---

## 11. Time and randomness

Determinism is non-negotiable. Pin both via `monkeypatch` or injection:

```python
def test_generate_token_uses_seeded_rng():
    # given
    import random
    rng = random.Random(42)
    class_under_test = TokenGenerator(rng=rng)
    # when
    result = class_under_test.generate()
    # then
    assert result == "expected_token_value"
```

Without pinning time and randomness, tests fail the **Repeatable** principle from SKILL.md §4. Inject a seeded `Random` instance rather than letting production code call `random.random()` directly.

---

## 12. Mocking

### Hierarchy of preference

1. **Real object** — for value types, DTOs, pure functions.
2. **Fake (in-memory implementation)** — for repositories, caches. Often the cleanest choice.
3. **`monkeypatch`** — for module-level functions, environment, attributes.
4. **`unittest.mock.MagicMock` / `patch`** — for object-level collaborators.

### `monkeypatch`

For replacing module-level state during a test:

```python
from datetime import datetime


def test_fetches_from_configured_url(monkeypatch):
    # given
    monkeypatch.setenv("API_URL", "https://test.example.com")
    monkeypatch.setattr("myapp.clock.now", lambda: datetime(2024, 1, 15, 12, 0, 0))
    # when
    result = fetch_config()
    # then
    assert result.base_url == "https://test.example.com"
```

### `MagicMock` and `patch`

For object-level mocks of injected collaborators, construct them in `# given`:

```python
def test_create_order_persists_order():
    # given
    mock_repository = MagicMock(spec=OrderRepository)
    mock_repository.save.return_value = Order(id="ord-1", total=Decimal("10"))
    class_under_test = OrderService(mock_repository)
    input_order = Order(id=None, total=Decimal("10"))
    # when
    result = class_under_test.create(input_order)
    # then
    assert result.id == "ord-1"
    mock_repository.save.assert_called_once_with(input_order)
```

Rules:
- **Use `spec=` whenever you mock a real class.** Without `spec`, a typo in a method name silently passes.
- Only call `assert_called_once_with(...)` / `assert_called_with(...)` when the call itself is the contract (i.e., a side effect like "save was invoked"). For return-value-driven behavior, assert on `result` instead.
- If using `patch` as a decorator, prefer `with patch(...) as mock_X` inside the test body — it keeps the mock visible in `# given`.

### Don't mock third-party libraries directly

Wrap external SDKs behind a port (your own interface/protocol) and mock the port. This protects tests from SDK API changes.

---

## 13. Async tests

If the project uses `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_returns_payload():
    # given
    class_under_test = AsyncFetcher(timeout=1.0)
    # when
    result = await class_under_test.fetch("/health")
    # then
    assert result.status == 200
```

Configure `asyncio_mode = "auto"` in `pyproject.toml` if the project does so — then the marker can be omitted.

---

## 14. Skeleton for a new test module

```python
"""Tests for myapp.orders.service."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from myapp.orders.errors import InvalidOrderError
from myapp.orders.models import Order, Status
from myapp.orders.repository import OrderRepository
from myapp.orders.service import OrderService


@pytest.fixture
def mock_repository():
    return MagicMock(spec=OrderRepository)


@pytest.fixture
def class_under_test(mock_repository):
    return OrderService(mock_repository)


def test_create_order_valid_cart_persists_order(class_under_test, mock_repository):
    # given
    input_order = Order(id=None, customer_id="cust-1", total=Decimal("10"))
    mock_repository.save.return_value = input_order.with_id("ord-1")
    # when
    result = class_under_test.create(input_order)
    # then
    assert result.id == "ord-1"
    assert result.status == Status.PENDING


def test_create_order_zero_total_raises_validation_error(class_under_test):
    # given
    input_order = Order(id=None, customer_id="cust-1", total=Decimal("0"))
    # when / then
    with pytest.raises(InvalidOrderError, match="total must be positive"):
        class_under_test.create(input_order)


@pytest.mark.parametrize(
    "total, expected_status",
    [
        (Decimal("0.01"), Status.PENDING),
        (Decimal("99999.99"), Status.PENDING_REVIEW),
    ],
    ids=["minimum_positive_total", "large_total_requires_review"],
)
def test_create_order_assigns_status_based_on_total(class_under_test, mock_repository, total, expected_status):
    # given
    input_order = Order(id=None, customer_id="cust-1", total=total)
    mock_repository.save.side_effect = lambda o: o.with_id("ord-x")
    # when
    result = class_under_test.create(input_order)
    # then
    assert result.status == expected_status
```

---

## 15. Features explicitly NOT used

Do not introduce without a strong reason:

- `unittest.TestCase` class-based tests (use plain functions).
- `self.assertEqual` / `self.assertTrue` (use plain `assert`).
- `setUp` / `tearDown` methods (use fixtures).
- Auto-generated parametrize IDs for non-trivial cases (always supply `ids=`).
- Module/session-scoped fixtures for mutable state.
- `MagicMock()` without `spec=` for known classes.
- Asserting interaction counts (`assert_called_once`, `call_count`) when the return value or state change is the real contract.

---

## 16. Quick reference

| Task                              | How                                                                |
|-----------------------------------|--------------------------------------------------------------------|
| Test function                     | `def test_<func>_<scenario>_<expected>(): ...`                     |
| Parameterized test                | `@pytest.mark.parametrize("a, b", [...], ids=[...])`               |
| Fixture                           | `@pytest.fixture` (function-scoped by default)                     |
| Shared fixtures                   | `conftest.py`                                                      |
| Subject-under-test variable       | `class_under_test`                                                 |
| Result variable                   | `result`                                                           |
| Equality                          | `assert result == expected`                                        |
| Identity                          | `assert result is None` / `is x`                                   |
| Membership                        | `assert "x" in collection`                                         |
| Floats                            | `assert result == approx(expected)`                                |
| Unordered                         | `assert sorted(result) == sorted(expected)` or `set(...) == set(...)` |
| Exception                         | `with pytest.raises(Err, match="..."): ...`                        |
| Mock collaborator                 | `MagicMock(spec=Class)` then `.method.return_value = ...`          |
| Module-level patching             | `monkeypatch.setattr("pkg.module.name", value)`                    |
| Env var                           | `monkeypatch.setenv("KEY", "value")`                               |
| Temp file/dir                     | `tmp_path` fixture                                                 |
| Capture stdout/stderr             | `capsys` fixture                                                   |
| Capture logs                      | `caplog` fixture                                                   |
| Verify a side-effect call         | `mock.method.assert_called_once_with(args)` (only when call IS the contract) |
