# JavaScript Unit Test Reference — Jest (and Vitest)

Prescriptive guide for writing JavaScript/TypeScript unit tests with **Jest**. The same patterns work with **Vitest** — the API is almost identical (`import { describe, it, expect, vi } from "vitest"` and `vi.fn()` / `vi.spyOn()` in place of `jest.fn()` / `jest.spyOn()`).

**Stack**: Jest (or Vitest) • `expect` matchers • `jest.fn()` / `jest.spyOn()` / `jest.mock()` for doubles • `it.each` / `test.each` for parameterized cases.

> **Always check the project's existing tests first.** If the project uses Mocha + Chai, Jasmine, or AVA, follow that style. If it uses Vitest, use `vi` instead of `jest`. The reference is the default for greenfield code.

This reference follows the **FIRST-U** principles (Fast, Isolated, Repeatable, Self-validating, Timely, Understandable) defined in §4 of the main skill. Every test here should satisfy each letter.

---

## 1. Tooling

- **Jest** as the default test runner, or **Vitest** (nearly identical API — replace `jest.*` with `vi.*`; equivalents appear in the Quick reference).
- **`expect`** built-in matchers for all assertions — no Chai, no power-assert.
- **`jest.fn()`** / **`jest.spyOn()`** for test doubles; **`jest.mock()`** for whole-module replacement.
- **`it.each`** / **`test.each`** for parameterized cases.
- No Mocha, no Jasmine, no AVA — if the project uses one, follow its style instead.

---

## 2. File layout

Two acceptable conventions — match the project's existing layout:

- **Sibling**: `src/orders/orderService.ts` → `src/orders/orderService.test.ts`
- **`__tests__` directory**: `src/orders/orderService.ts` → `src/orders/__tests__/orderService.test.ts`

Naming:
- File: `<source>.test.ts` (or `.test.js`, `.spec.ts`, `.spec.js` — follow the project).
- One test file per production module.

---

## 3. What to test, by layer

| Layer | Mock | Don't mock | Focus |
|-------|------|------------|-------|
| **Route handlers** | Service layer | — | Input validation, auth, response shape (status, body) |
| **Services / use cases** | Repository, client | Internal pure modules | Business logic: given state + inputs, verify outputs and side effects |
| **Pure functions / transformers** | Nothing | Everything | Input → output mapping. `it.each` for parameterized cases. |
| **External clients** | `nock` / `msw` — not the SDK directly | — | Request shape (method, URL, headers) and every response branch |
| **Event handlers** | Event bus mock | — | Payload schema, behavior on valid/malformed/duplicate events |

---

## 4. Block structure — `describe` + `it`

Group tests by the unit (class or function) using `describe`. Inside, use `it` for individual cases. Read them as: *"<unit> — <scenario> — <expected behavior>."*

```typescript
describe("OrderService", () => {
  describe("createOrder", () => {
    it("persists a valid order and returns it with an assigned id", async () => {
      // given
      const mockRepository = { save: jest.fn().mockResolvedValue({ id: "ord-1", total: 10 }) };
      const classUnderTest = new OrderService(mockRepository);
      const input = { customerId: "cust-1", total: 10 };
      // when
      const result = await classUnderTest.create(input);
      // then
      expect(result.id).toBe("ord-1");
      expect(mockRepository.save).toHaveBeenCalledWith(input);
    });
  });
});
```

Rules:
- Outer `describe` is the **production unit name** (class, module, or function).
- Inner `describe` (optional) is the **method or function name** under test.
- `it` describes the scenario and the expected outcome — full sentence, lowercase except for proper nouns.
- Don't use `should` prefixes (`should return ...`); use the present tense (`returns ...`, `rejects ...`).
- Prefer `it` over `test` — pairs naturally with `describe`. Pick one and stay consistent.

### Test name examples

```typescript
it("returns null for an unknown user")                                // ✅
it("throws OverdraftError when balance is insufficient")              // ✅
it("creates the order and sends a confirmation email")                // ✅
it("rejects requests without an authorization header")                // ✅
it("should return null")                                              // ❌ avoid `should`
it("test1")                                                           // ❌ generic
```

---

## 5. Given / When / Then comments

Use lowercase block comments inside each `it`:

```typescript
it("returns the parsed date for an ISO string", () => {
  // given
  const classUnderTest = new DateParser();
  const input = "2024-03-15";
  // when
  const result = classUnderTest.parse(input);
  // then
  expect(result).toEqual(new Date("2024-03-15"));
});
```

Rules:
- Write `// given`, `// when`, `// then` markers **only if the existing project tests already use them**; if they don't, keep the same three-block structure without comments.
- When used, always lowercase, no colons: `// given`, `// when`, `// then`.
- `// when` is **one statement** — the call under test (`const result = ...`).
- All `expect(...)` calls live under `// then`.
- Omit `// given` only when there is genuinely no setup beyond what's in `beforeEach`.

---

## 6. Canonical variable names

| Variable          | Meaning                                                       |
|-------------------|---------------------------------------------------------------|
| `classUnderTest`  | The instance whose behavior is being tested. Always this name. For free functions, call the function directly. |
| `result`          | The return value of the function under test.                  |
| `expected`        | The expected value, when it needs a name.                     |
| `mock<Thing>`     | A mock collaborator (`mockRepository`, `mockClock`).          |

Use **the same parameter names** as the function under test for inputs.

---

## 7. `expect` matchers — catalogue

Prefer the most specific matcher for the type.

### Equality

```typescript
expect(result).toBe(42);                  // === (primitives, references)
expect(result).toEqual({ id: 1, name: "alice" });  // deep equality
expect(result).toStrictEqual(expected);   // also checks no extra undefined keys / types
expect(result).toMatchObject({ id: 1 });  // subset match for objects
```

### Truthiness

```typescript
expect(value).toBeNull();
expect(value).toBeUndefined();
expect(value).toBeDefined();
expect(value).toBeTruthy();
expect(value).toBeFalsy();
expect(flag).toBe(true);
expect(flag).toBe(false);
```

### Numbers

```typescript
expect(count).toBe(0);
expect(elapsed).toBeGreaterThanOrEqual(100);
expect(price).toBeLessThan(50);
expect(value).toBeCloseTo(0.3, 5);  // floats — 5 decimal places
```

### Strings

```typescript
expect(message).toBe("exact message");
expect(message).toContain("substring");
expect(message).toMatch(/^Error: /);
```

### Arrays and iterables

```typescript
expect(items).toHaveLength(3);
expect(items).toContain("apple");
expect(items).toEqual(["a", "b", "c"]);                    // order matters
expect(items).toEqual(expect.arrayContaining(["a", "b"])); // contains subset, any order
```

### Objects

```typescript
expect(obj).toHaveProperty("user.email", "alice@example.com");
expect(obj).toMatchObject({ status: "PENDING" });  // partial match
```

### Async

```typescript
await expect(promise).resolves.toEqual({ ok: true });
await expect(promise).rejects.toThrow(NetworkError);
await expect(promise).rejects.toThrow("Connection refused");
```

### Snapshots

Use **sparingly**. Snapshots are powerful but easy to abuse — they're appropriate for stable, deterministic output (config files, generated HTML/JSON) but bad for anything that changes with every iteration.

```typescript
expect(result).toMatchSnapshot();          // file snapshot
expect(result).toMatchInlineSnapshot(`...`);  // inline snapshot — preferred for small outputs
```

---

## 8. Exception testing — `toThrow`

```typescript
it("throws OverdraftError when balance is insufficient", () => {
  // given
  const classUnderTest = new Account(50);
  // when / then
  expect(() => classUnderTest.withdraw(100)).toThrow(OverdraftError);
  expect(() => classUnderTest.withdraw(100)).toThrow("Withdrawal exceeds balance");
});
```

Or capture the error explicitly when you need to assert on multiple properties:

```typescript
it("throws OverdraftError with the requested amount", () => {
  // given
  const classUnderTest = new Account(50);
  // when
  let caught: Error | undefined;
  try {
    classUnderTest.withdraw(100);
  } catch (e) {
    caught = e as Error;
  }
  // then
  expect(caught).toBeInstanceOf(OverdraftError);
  expect((caught as OverdraftError).requested).toBe(100);
});
```

For async:

```typescript
await expect(classUnderTest.create(invalidOrder)).rejects.toThrow(InvalidOrderError);
```

---

## 9. Parameterized tests — `it.each` / `test.each`

```typescript
describe("HttpMethod.fromString", () => {
  it.each([
    ["get",     HttpMethod.GET],
    ["GET",     HttpMethod.GET],
    ["post",    HttpMethod.POST],
    ["invalid", null],
  ])("returns %p for input %p", (input, expected) => {
    // when
    const result = HttpMethod.fromString(input);
    // then
    expect(result).toBe(expected);
  });
});
```

For richer cases, use the object form:

```typescript
it.each([
  { name: "lowercase get",        input: "get",     expected: HttpMethod.GET },
  { name: "uppercase get",        input: "GET",     expected: HttpMethod.GET },
  { name: "unknown returns null", input: "invalid", expected: null },
])("$name", ({ input, expected }) => {
  // when
  const result = HttpMethod.fromString(input);
  // then
  expect(result).toBe(expected);
});
```

Rules:
- Use the object form when there are 3+ columns — names stay readable.
- Each row should include a descriptive `name` (the `$name` placeholder displays it in test output).

---

## 10. Test doubles

### Hierarchy of preference

1. **Real object** — for value types, DTOs, pure helpers.
2. **In-memory fake** — for repositories or other stateful collaborators when one exists.
3. **`jest.fn()` / `jest.spyOn()`** — for individual functions.
4. **`jest.mock()`** — for whole modules.

### `jest.fn()` — anonymous mock function

```typescript
const mockRepository = {
  save: jest.fn().mockResolvedValue({ id: "ord-1" }),
  findById: jest.fn().mockResolvedValue(null),
};
```

### `jest.spyOn()` — wraps a real method

Use when you want real behavior plus asserting on calls (a spy):

```typescript
const spy = jest.spyOn(logger, "warn");
// when
classUnderTest.handle(invalidInput);
// then
expect(spy).toHaveBeenCalledWith("invalid input received");
```

Always restore spies in cleanup or use `mockRestore()` to avoid leaking into other tests:

```typescript
afterEach(() => {
  jest.restoreAllMocks();
});
```

### `jest.mock()` — module mocking

```typescript
jest.mock("../external/paymentGateway");

import { charge } from "../external/paymentGateway";

beforeEach(() => {
  (charge as jest.Mock).mockResolvedValue({ id: "txn-1", status: "succeeded" });
});
```

Hoisting note: `jest.mock(...)` calls are hoisted to the top of the file by Jest. You don't need to put them before the imports.

### TypeScript: typing mocks

Two patterns — choose based on context:

```typescript
// Pattern A: jest.Mocked<T> — use when you inject via interface or type
// Gives full type-safe access to .mockReturnValue, .mockResolvedValue, etc.
let mockRepository: jest.Mocked<OrderRepository>;
mockRepository = { save: jest.fn(), findById: jest.fn() } as jest.Mocked<OrderRepository>;

// Pattern B: `as unknown as T` — use when Pattern A produces excess-property errors
// or the mock literal doesn't satisfy the interface exactly
classUnderTest = new OrderService(mockRepository as unknown as OrderRepository);
```

Prefer Pattern A: `jest.Mocked<T>` carries the mock method types so `.mockResolvedValue(...)` is fully typed without a cast. Fall back to `as unknown as T` only when structural mismatches make `as jest.Mocked<T>` error.

### Don't mock third-party libraries directly

Wrap external SDKs behind your own port/adapter and mock the adapter. This shields tests from SDK API changes.

### Verifying calls vs. asserting on result

- `expect(mock).toHaveBeenCalledWith(...)` only when the call itself is the contract (a side effect like "sendEmail was invoked with the right recipient").
- The negative form matters too — assert a side effect was **not** triggered when that is the contract:

```typescript
it("does not send email on dry-run", async () => {
  // given
  const mockEmailService = { send: jest.fn() };
  const classUnderTest = new OrderService(mockEmailService, { dryRun: true });
  // when
  await classUnderTest.create({ customerId: "cust-1", total: 10 });
  // then
  expect(mockEmailService.send).not.toHaveBeenCalled();
});
```

- Otherwise assert on `result` or the resulting state.

---

## 11. Lifecycle hooks

- `beforeEach` — set up state shared by every test in the block. Use it for cheap setup that should run anew per test (default).
- `afterEach` — clean up resources, restore mocks (`jest.restoreAllMocks()`).
- `beforeAll` / `afterAll` — only for genuinely expensive, **immutable** setup. The wrong choice causes flakes.

```typescript
describe("OrderService", () => {
  let classUnderTest: OrderService;
  let mockRepository: jest.Mocked<OrderRepository>;

  beforeEach(() => {
    mockRepository = { save: jest.fn(), findById: jest.fn() } as any;
    classUnderTest = new OrderService(mockRepository);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("...", () => { /* ... */ });
});
```

---

## 12. Time and randomness

Determinism is non-negotiable. Pin both.

### Fake timers

```typescript
beforeEach(() => {
  jest.useFakeTimers().setSystemTime(new Date("2024-01-15T12:00:00Z"));
});

afterEach(() => {
  jest.useRealTimers();
});
```

Use `jest.advanceTimersByTime(ms)` to move time forward inside a test.

### Randomness

Inject a `Random` interface (or pass a seeded generator) so the test can supply a deterministic source. Don't `jest.spyOn(Math, "random")` unless you must — the wrapped-port pattern is cleaner.

---

## 13. Async tests

- Always use `async`/`await` over `.then()` chains.
- For promise rejection, use `await expect(...).rejects.toThrow(...)`.
- Don't forget `await` on async assertions — Jest won't fail a missed-await; it'll just silently miss the rejection.

```typescript
it("fetches the payload from the configured URL", async () => {
  // given
  const classUnderTest = new ApiClient("https://api.example.com");
  // when
  const result = await classUnderTest.fetchUser("u-1");
  // then
  expect(result).toEqual({ id: "u-1", name: "alice" });
});
```

---

## 14. Skeleton

```typescript
import { OrderService } from "./orderService";
import { Order, Status } from "./order";
import { InvalidOrderError } from "./errors";

describe("OrderService", () => {
  let mockRepository: { save: jest.Mock; findById: jest.Mock };
  let classUnderTest: OrderService;

  beforeEach(() => {
    mockRepository = { save: jest.fn(), findById: jest.fn() };
    classUnderTest = new OrderService(mockRepository as any);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("create", () => {
    it("persists a valid order and returns it with an assigned id", async () => {
      // given
      const input: Order = { id: null, customerId: "cust-1", total: 10 };
      mockRepository.save.mockResolvedValue({ ...input, id: "ord-1" });
      // when
      const result = await classUnderTest.create(input);
      // then
      expect(result.id).toBe("ord-1");
      expect(result.status).toBe(Status.PENDING);
      expect(mockRepository.save).toHaveBeenCalledWith(input);
    });

    it("throws InvalidOrderError when total is zero", async () => {
      // given
      const input: Order = { id: null, customerId: "cust-1", total: 0 };
      // when / then
      await expect(classUnderTest.create(input)).rejects.toThrow(InvalidOrderError);
      await expect(classUnderTest.create(input)).rejects.toThrow("total must be positive");
    });
  });

  describe("findById", () => {
    it.each([
      { name: "returns the order when found",     repoReturn: { id: "ord-1" }, expected: { id: "ord-1" } },
      { name: "returns null when no order found", repoReturn: null,            expected: null },
    ])("$name", async ({ repoReturn, expected }) => {
      // given
      mockRepository.findById.mockResolvedValue(repoReturn);
      // when
      const result = await classUnderTest.findById("ord-1");
      // then
      expect(result).toEqual(expected);
    });
  });
});
```

---

## 15. Features explicitly NOT used

Do not introduce without a strong reason:

- `should` prefix in test names.
- Snapshot tests for output that changes frequently.
- `beforeAll` / `afterAll` for mutable setup (use `beforeEach`).
- `toEqual` when `toBe` works (primitives) — `toBe` is clearer.
- `expect(mock).toHaveBeenCalled()` without arguments when you care about the arguments — be specific.
- Mixed `test`/`it` in the same file — pick one.

---

## 16. Quick reference

| Task                              | How                                                                |
|-----------------------------------|--------------------------------------------------------------------|
| Group by unit                     | `describe("UnitName", () => { ... })`                              |
| Single test                       | `it("describes scenario and outcome", () => { ... })`              |
| Parameterized                     | `it.each([{ name, ... }])("$name", ({ ... }) => { ... })`          |
| Setup                             | `beforeEach`                                                       |
| Restore spies                     | `afterEach(() => jest.restoreAllMocks())`                          |
| Subject-under-test variable       | `classUnderTest`                                                   |
| Result variable                   | `result`                                                           |
| Primitive equality                | `expect(x).toBe(y)`                                                |
| Deep equality                     | `expect(x).toEqual(y)`                                             |
| Subset match                      | `expect(x).toMatchObject({ ... })`                                 |
| Async resolve                     | `await expect(p).resolves.toEqual(...)`                            |
| Async reject                      | `await expect(p).rejects.toThrow(ErrorClass)`                      |
| Mock function                     | `jest.fn().mockResolvedValue(...)`                                 |
| Spy a real method                 | `jest.spyOn(obj, "method")`                                        |
| Module mock                       | `jest.mock("../path")` (hoisted)                                   |
| Verify call (only if call IS the contract) | `expect(mock).toHaveBeenCalledWith(...)`                  |
| Pin time                          | `jest.useFakeTimers().setSystemTime(new Date("..."))`              |
| Advance time                      | `jest.advanceTimersByTime(ms)`                                     |

### Vitest equivalents

| Jest              | Vitest                       |
|-------------------|------------------------------|
| `jest.fn()`       | `vi.fn()`                    |
| `jest.spyOn(...)` | `vi.spyOn(...)`              |
| `jest.mock(...)`  | `vi.mock(...)`               |
| `jest.useFakeTimers()` | `vi.useFakeTimers()`    |
| `jest.advanceTimersByTime(ms)` | `vi.advanceTimersByTime(ms)` |
| `jest.Mocked<T>`  | `vi.Mocked<T>` (or `Mocked<T>` from `vitest`) |

Imports for Vitest:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
```
