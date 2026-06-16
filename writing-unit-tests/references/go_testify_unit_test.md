# Go Unit Test Reference — testify

Conventions for writing Go unit tests using **testify** (`assert` + `require`). Following it produces tests indistinguishable from existing ones in the project.

> **Always check the project's existing tests first.** If the project uses stdlib-only, follow `go_std_unit_test.md` instead.

This reference follows the **FIRST-U** principles (Fast, Isolated, Repeatable, Self-validating, Timely, Understandable) defined in §4 of the main skill. Every test here should satisfy each letter.

---

## 1. Tooling

- `testing` package + `github.com/stretchr/testify/assert` + `github.com/stretchr/testify/require` (when needed).
- For HTTP, `net/http/httptest` plus the project's framework.
- Mocking: use testify's `mock` package, hand-rolled mocks, or in-memory fakes — match what the project already does.

---

## 2. File organisation

- Same package as the code under test (white-box).
- Each source `foo.go` has a corresponding `foo_test.go`.
- Don't create a shared `all_test.go`.

---

## 3. What to test, by layer

| Layer | Mock | Don't mock | Focus |
|-------|------|------------|-------|
| **HTTP handlers** | Service interface | — | Parameter validation, auth checks, response status/body |
| **Services / use cases** | Repository interface | Internal pure modules | Business logic: given state + inputs, verify outputs and side effects |
| **Builders / mappers** | Nothing | Everything | Input → output mapping. Table-driven tests. |
| **External clients** | `httptest` server — not the SDK directly | — | Request shape (method, path, headers) and every response branch (2xx, 4xx, 5xx, timeout, malformed) |
| **Event producers / consumers** | Bus / broker interface | — | Payload schema, behavior on valid/malformed/duplicate events |

---

## 4. Given / When / Then

Every test that performs a discrete operation has three sections:

```go
func TestDequeue(t *testing.T) {
	// given
	q := New[int]()
	q.Enqueue(10)
	q.Enqueue(20)
	// when
	result, ok := q.Dequeue()
	// then
	assert.True(t, ok)
	assert.Equal(t, 10, result)
}
```

Rules:
- Write `// given`, `// when`, `// then` markers **only if the existing project tests already use them**; if they don't, keep the same three-block structure without comments.
- When used: `// given` — all state setup, object construction, preparation.
- `// when` — **only the call being tested**. Side effects of setup (cache prepopulation, etc.) belong in `// given`.
- `// then` — all assertions.
- If the call returns a value, assign it to `result`. Secondary returns (`ok`, `err`) keep their semantic names.
- Expected values declared in `// then` are prefixed with `expected` (e.g., `expected`, `expectedMatch`, `expectedLen`).

```go
// when
result, ok := cache.Get("key")
// then
assert.True(t, ok)
expected := 42
assert.Equal(t, expected, result)
```

---

## 5. `assert` vs `require`

Use `assert` (non-fatal — every failure reported, test continues) **by default**.

Use `require` (fatal — stops the test) **only** when continuing would:
- **Panic** (calling a method on a nil pointer/interface),
- Or make remaining assertions **meaningless** (setup failed; the rest of the test is invalid).

```go
// require: q is nil on error; q.Enqueue would panic
q, err := NewBlockingQueue[int](3)
require.NoError(t, err)
q.Enqueue(10)

// require: result is a pointer; result.Cap() panics if nil
result, err := NewLRUCache[string, int](WithCapacity(3))
require.NoError(t, err)
assert.Equal(t, 3, result.Cap())

// assert: result is a plain int; no panic risk
result, err := sf.Do("key", provider).Await(ctx)
assert.NoError(t, err)
assert.Equal(t, 42, result)
```

Do **not** reach for `require` just because a test "feels done" after the first failure. Ask: would continuing panic, or produce misleading output?

### Common calls

```go
assert.NoError(t, err)
assert.ErrorIs(t, err, ErrSomething)
assert.True(t, ok)
assert.False(t, ok)
assert.NotNil(t, result)
assert.Equal(t, expected, result)          // scalars, ordered slices
assert.ElementsMatch(t, expected, result)  // unordered (sets, maps)
assert.Empty(t, result)
assert.Contains(t, str, "substring")
```

> Note: `assert.Equal` uses `reflect.DeepEqual` and distinguishes `nil` from `[]T{}`. For iterator results that may be `nil` on empty input, prefer `assert.ElementsMatch` or `assert.Empty` over `assert.Equal(t, []T{}, result)`.

---

## 6. Test function structure

### Single scenario → top-level `Test<Func>`

```go
func TestDequeue(t *testing.T) { ... }
```

### Multiple scenarios → `t.Run` subtests

When a function has multiple meaningful scenarios, group them under one parent and use subtests:

```go
func TestPop(t *testing.T) {
	t.Run("non-empty stack", func(t *testing.T) {
		// given
		s := New[int]()
		s.Push(1)
		s.Push(2)
		// when
		result, ok := s.Pop()
		// then
		assert.True(t, ok)
		assert.Equal(t, 2, result)
	})

	t.Run("empty stack", func(t *testing.T) {
		// given
		s := New[int]()
		// when
		result, ok := s.Pop()
		// then
		assert.False(t, ok)
		assert.Equal(t, 0, result)
	})
}
```

Every `t.Run` body must follow GWT.

### Don't create `_CaseName` functions

```go
// Wrong
func TestPop(t *testing.T)      { ... }
func TestPopEmpty(t *testing.T) { ... }

// Correct
func TestPop(t *testing.T) {
	t.Run("non-empty stack", ...)
	t.Run("empty stack",     ...)
}
```

---

## 7. Table-driven tests

```go
func TestFilter(t *testing.T) {
	isEven := func(v int) bool { return v%2 == 0 }

	tests := []struct {
		name     string
		input    []int
		expected []int
	}{
		{name: "nil input",    input: nil,            expected: []int{}},
		{name: "none pass",    input: []int{1, 3, 5}, expected: []int{}},
		{name: "all pass",     input: []int{2, 4, 6}, expected: []int{2, 4, 6}},
		{name: "partial pass", input: []int{1, 2, 3}, expected: []int{2}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			// given
			input := tc.input
			// when
			result := Filter(input, isEven)
			// then
			assert.Equal(t, tc.expected, result)
		})
	}
}
```

Rules:
- Struct field for expected value: `expected` (or `expectedXxx` when multiple outputs).
- Extract `tc.input` into a local `input` in `// given`.
- A table-driven test may be followed by additional explicit `t.Run` calls for special cases that don't fit the table.

---

## 8. Naming

Go convention favors short, semantic names. Unlike other language references, this ref does not prescribe `classUnderTest` — use names that read naturally in Go (`s`, `q`, `service`).

| Concept | Name | Example |
|---|---|---|
| Primary return value | `result` | `result, ok := s.Pop()` |
| Found indicator | `ok` | `result, ok := cache.Get(key)` |
| Error return | `err` | `result, err := lp.Get(ctx, k)` |
| Expected (local) | `expected` (or `expectedXxx`) | `expected := []int{1, 2, 3}` |
| Expected (struct field) | `expected` (or `expectedXxx`) | `expected bool` |
| Setup object | Short semantic name (`s`, `q`, `c`, `u`, `service`) | `s := New[int]()` |
| Multiple results (same op) | `result1`, `result2` | `result1, err1 := f.Await(ctx)` |

Function naming:
- `Test<Func>` — single scenario or parent of subtests.
- `Test<Func>With<Condition>` / `Test<Func>When<Condition>` — only when not using subtests.
- CamelCase, no underscores. Names describe the operation, not the expected outcome.

---

## 9. Test helper functions

Extract repeated setup into helpers when it appears in three or more tests.

```go
func mustNewLRUCache[K comparable, V any](t testing.TB, capacity int) *LRUCache[K, V] {
	t.Helper()
	c, err := NewLRUCache[K, V](capacity)
	if err != nil {
		t.Fatalf("NewLRUCache(%d): unexpected error: %v", capacity, err)
	}
	return c
}
```

Rules:
- Call `t.Helper()` as the first statement so failure lines point to the caller.
- Accept `testing.TB` (not `*testing.T`) so the helper works in tests and benchmarks.
- Name helpers `mustXxx` when they terminate on error.
- Use `t.Fatalf` directly in helpers (not `assert`/`require`).

---

## 10. Unordered collections

Use `assert.ElementsMatch` instead of sorting and comparing:

```go
result := s.Union(other).ToSlice()
assert.ElementsMatch(t, []int{1, 2, 3, 4}, result)
```

For `String()` methods on unordered collections, verify presence with `Contains` and shape with `Regexp`:

```go
result := s.String()
assert.Regexp(t, `^set\{.*\}$`, result)
assert.Contains(t, result, "1")
assert.Contains(t, result, "2")
```

---

## 11. Iterator / re-iteration tests

When testing functions that return `iter.Seq[T]` or `iter.Seq2[K, V]`, include a re-iteration subtest to verify state is not shared:

```go
t.Run("multiple iterations", func(t *testing.T) {
	// given
	input := []int{1, 2, 1, 3}
	seq := DistinctSeq(slices.Values(input))
	// when
	first := slices.Collect(seq)
	second := slices.Collect(seq)
	// then
	expected := []int{1, 2, 3}
	assert.Equal(t, expected, first)
	assert.Equal(t, expected, second, "state leaked across iterations")
})
```

---

## 12. Context

Use `t.Context()` — it's cancelled automatically when the test and its subtests finish.

```go
// Correct
result, err := lp.GetWithContext(t.Context(), "key")

// Wrong — unbounded, no test lifecycle
result, err := lp.GetWithContext(context.Background(), "key")
```

Reserve `context.WithTimeout` / `WithCancel` for tests **specifically testing timeout or cancellation**, and always derive from `t.Context()`:

```go
ctx, cancel := context.WithTimeout(t.Context(), 5*time.Millisecond)
defer cancel()
_, err := f.AwaitWithContext(ctx)
assert.ErrorIs(t, err, context.DeadlineExceeded)
```

---

## 13. Concurrency tests

Named constant for goroutine count, `sync.WaitGroup` to synchronise:

```go
func TestSyncStackConcurrentPush(t *testing.T) {
	// given
	const goroutines = 100
	s := NewSyncStack[int]()
	var wg sync.WaitGroup
	// when
	for i := range goroutines {
		wg.Add(1)
		go func(v int) {
			defer wg.Done()
			s.Push(v)
		}(i)
	}
	wg.Wait()
	// then
	assert.Equal(t, int64(goroutines), s.Len())
}
```

Run with `go test -race ./...` to catch data races.

---

## 14. Nil-safety tests

Functions or data structures that document nil-safe behaviour must have a dedicated test exercising every nil-safe operation:

```go
func TestSetNilSafety(t *testing.T) {
	// given
	var s Set[int]
	// then
	assert.Equal(t, 0, s.Len())
	assert.False(t, s.Contains(1))
	assert.Empty(t, s.ToSlice())
	s.Remove(1) // must not panic
}
```

---

## 15. Hand-rolled mocks (when not using testify's `mock.Mock`)

Define a file-local struct whose fields are function values matching the interface:

```go
type mockedTaskService struct {
    createTaskFunc      func(task *Task) error
    getTasksForUserFunc func(user *users.User) ([]*Task, error)
}

func (m *mockedTaskService) CreateTask(task *Task) error {
    return m.createTaskFunc(task)
}

func (m *mockedTaskService) GetTasksForUser(user *users.User) ([]*Task, error) {
    return m.getTasksForUserFunc(user)
}
```

Per-test setup populates only the relevant fields:

```go
mockedTaskService := &mockedTaskService{
    createTaskFunc: func(task *Task) error {
        task.ID = 1
        return nil
    },
}
```

## 16. Handler-level tests — canonical recipe

```go
func TestHandlerCreateTask(t *testing.T) {
	t.Run("creates task and returns 201", func(t *testing.T) {
		// given
		mockedTaskService := &mockedTaskService{
			createTaskFunc: func(task *Task) error {
				task.ID = 1
				return nil
			},
		}
		handler := NewHandler(mockedTaskService)

		e := tests.SetupEcho()
		req := tests.SetupRequest(http.MethodPost, "/v1/tasks", `{"summary":"Onboarding call"}`)
		rec := httptest.NewRecorder()
		context := e.NewContext(req, rec)
		security.SetAuthenticatedUser(context, &users.User{ID: 1, Username: "alice"})
		// when
		err := handler.CreateTask(context)
		// then
		assert.NoError(t, err)
		assert.Equal(t, http.StatusCreated, rec.Code)

		var taskResponse TaskResponse
		err = json.Unmarshal(rec.Body.Bytes(), &taskResponse)
		assert.NoError(t, err)
		assert.Equal(t, 1, taskResponse.ID)
	})
}
```

Conventions:
1. Build the mocked service first, populating only the function fields the test exercises.
2. Wire HTTP scaffolding via the project's helpers (`tests.SetupEcho()`, etc.).
3. For authenticated routes, inject the user. For unauthorized tests, **omit** this call.
4. Invoke the handler method **directly** — do not route through the framework's mux.
5. Assert in this order: returned `err`, status code, body (decoded JSON).

## 17. Service-level tests — canonical recipe

```go
func TestCreateUser(t *testing.T) {
	t.Run("persists user and assigns ID", func(t *testing.T) {
		// given
		userRepo := NewInMemoryUserRepository()
		userService := NewService(userRepo)
		user := &User{Username: "alice", Password: "S3cur3!", Role: Manager}
		// when
		err := userService.CreateUser(user)
		// then
		require.NoError(t, err)
		savedUser, err := userService.UserByUsername(user.Username)
		assert.Equal(t, user, savedUser)
	})
}
```

Conventions:
- Compose with the **real** in-memory repository, not a mock.
- Verify side effects by calling another public method — not by reaching into internals.
- For domain errors, compare with sentinels using `errors.Is`:

```go
assert.ErrorIs(t, err, ErrDuplicatedUsername)
```

## 18. Boundary (DTO mapping) tests

```go
func TestToTask(t *testing.T) {
	// given
	user := &users.User{ID: 1, Username: "alice", Role: users.Technician}
	request := &TaskCreateRequest{Summary: "Onboarding call"}
	// when
	task := request.toTask(user)
	// then
	assert.Equal(t, request.Summary, task.Summary)
	assert.Equal(t, user.ID, task.Assignee.ID)
}
```

- Test unexported helpers directly (same-package).
- One assertion per mapped field — don't fold into deep-equal.

---

## 19. Exception and error testing

Use `assert.ErrorIs` for sentinel errors and `assert.ErrorAs` for concrete error types. Both are non-fatal — they allow the test to report further failures.

```go
// sentinel error
result, err := cache.Get(ctx, "missing")
assert.Nil(t, result)
assert.ErrorIs(t, err, ErrNotFound)

// concrete error type
result, err := parser.Parse("bad input")
assert.Nil(t, result)
var parseErr *ParseError
assert.ErrorAs(t, err, &parseErr)
assert.Equal(t, "bad input", parseErr.Input)
```

Use `require.NoError` when the rest of the test depends on the returned value:

```go
result, err := NewQueue[int](3)
require.NoError(t, err)   // nil-panic if result is nil
result.Enqueue(1)
```

Use `assert.Panics` to assert that a call panics:

```go
assert.Panics(t, func() {
	var s Stack[int]
	s.MustPop() // documented to panic on empty
})
```

---

## 20. Skeleton

```go
package mypackage

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestStack(t *testing.T) {
	t.Run("pop returns top element and true", func(t *testing.T) {
		// given
		s := New[int]()
		s.Push(1)
		s.Push(2)
		// when
		result, ok := s.Pop()
		// then
		assert.True(t, ok)
		assert.Equal(t, 2, result)
		assert.Equal(t, int64(1), s.Len())
	})

	t.Run("pop on empty stack returns zero value and false", func(t *testing.T) {
		// given
		s := New[int]()
		// when
		result, ok := s.Pop()
		// then
		assert.False(t, ok)
		assert.Equal(t, 0, result)
	})
}
```

---

## 21. Features explicitly NOT used

Do not introduce without a strong reason:

- `testify/suite` — class-based test grouping; use top-level `Test<Func>` + `t.Run` subtests.
- `mock.AssertExpectations(t)` as the only assertion — verify observable state or return values, not call counts, unless the call is the contract.
- `context.Background()` in tests — use `t.Context()` (§11).
- `time.Sleep` for synchronisation — use `sync.WaitGroup` or channels.
- Separate `TestFooCase1`, `TestFooCase2` top-level functions — group under one `TestFoo` with `t.Run` (§5).

---

## 22. Quick reference

```
TestFoo                      ← top-level function (one per public API entry point)
  t.Run("scenario A", ...)   ← explicit subtest with GWT
  t.Run("scenario B", ...)   ← explicit subtest with GWT
  for _, tc := range tests   ← table-driven loop, GWT in each t.Run body
    t.Run(tc.name, ...)

assert.Equal(t, expected, result)          ← ordered slices, scalars
assert.ElementsMatch(t, expected, result)  ← unordered (sets, maps, Seq outputs)
require.NoError(t, err)                    ← when next line would panic on err
```
