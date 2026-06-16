# Go Unit Test Reference — stdlib only

Conventions for writing Go unit tests with **only** the `testing` package. No testify, no gomock, no go-cmp. Following it produces tests indistinguishable from existing ones in the project.

> **Always check the project's existing tests first.** If the project uses testify or a different framework, follow `go_testify_unit_test.md` or the in-project style instead.

This reference follows the **FIRST-U** principles (Fast, Isolated, Repeatable, Self-validating, Timely, Understandable) defined in §4 of the main skill. Every test here should satisfy each letter.

---

## 1. Tooling

- `testing` package only.
- For HTTP, `net/http/httptest` plus the project's framework (e.g., Echo, chi, stdlib).
- No external mocking framework. Use **hand-rolled mocks** (§6).

If the project provides shared test helpers (`internal/tests/`), reuse them — don't inline equivalent boilerplate.

---

## 2. File and package layout

- Tests live **next to the production file**: `service.go` → `service_test.go`.
- Tests are **same-package (white-box)**: `package users`, not `package users_test`. This lets tests call unexported functions and methods directly.
- One test file per source file. Don't merge into a shared `all_test.go`.

Typical layered split inside a domain package:

| File | What it tests |
|---|---|
| `service_test.go` | Business-logic unit tests, exercised against real in-memory repositories. |
| `api_test.go` | HTTP handler tests with hand-rolled mocked services. |
| `boundary_test.go` | DTO ↔ domain mapping helpers (e.g., `toUser`, `toResponse`). |
| `entity_test.go` | Pure value types, enums, parsers. |

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

## 4. Test function naming

One top-level `Test<Func>` per function under test. Use `t.Run` subtests or table-driven tests inside it for multiple scenarios.

| Pattern | Use for | Example |
|---|---|---|
| `Test<Func>` | Entry point for all tests of a function | `TestCreateTask`, `TestHashPassword` |
| `TestHandler<Func>` | HTTP handler tests (prefix disambiguates from service-level tests of the same operation) | `TestHandlerCreateTask`, `TestHandlerCreateUser` |

Rules:
- CamelCase after `Test`. No underscores, no full sentences.
- Do **not** create `Test<Func>WithCondition` or `Test<Func>WhenCondition` as separate top-level functions — use a `t.Run` subtest or a table row instead.
- Use **table-driven tests** (§7) when scenarios vary only in input/output.
- Use **`t.Run` subtests** when scenarios have meaningfully different setup (e.g., authorised vs. unauthorised user, different mock responses).
- Each `t.Run` label describes the condition, not the expected outcome (e.g., `"unauthorized user"`, `"user does not exist"`).

---

## 5. Given / When / Then

Every test is annotated with three single-line lowercase comments:

```go
func TestCreateTask(t *testing.T) {
    t.Run("creates task successfully", func(t *testing.T) {
        // given
        taskRepository := NewInMemoryTaskRepository()
        notificationService := notifications.NewService()
        service := NewService(taskRepository, notificationService)
        user := &User{ID: 1, Username: "alice"}
        task := &Task{Summary: "Schedule onboarding call", Assignee: user}
        // when
        err := service.CreateTask(task)
        // then
        if err != nil {
            t.Errorf("expected no error, got %v", err)
        }
        if task.ID == 0 {
            t.Error("expected task ID to be set, got 0")
        }
    })
}
```

Rules:
- Write `// given`, `// when`, `// then` markers **only if the existing project tests already use them**; if they don't, keep the same three-block structure without comments.
- When used, always lowercase, no colons: `// given`, `// when`, `// then`.
- The `// when` block is normally **one statement** — the call under test (plus the assignment line if it returns).
- All assertions go in `// then`.
- Omit `// given` only when there is genuinely no setup.
- For table-driven tests, `// given` covers per-row setup extracted from `test`; `// when` and `// then` follow inside each `t.Run` body.

---

## 6. Variable naming

Go convention favors short, semantic names. Unlike other language references, this ref does not prescribe `classUnderTest` — use names that read naturally in Go (`service`, `handler`, `repo`).

| Role | Name |
|---|---|
| Primary return value | `result` |
| Boolean "found" / `ok` indicator | `ok` |
| Error return | `err` |
| Expected value (local) | `expected` (or `expectedXxx`) |
| Setup object under test | short semantic name (`service`, `handler`, `repo`) |
| Repository collaborator | `taskRepository`, `userRepo` |
| Hand-rolled mock instance | `mockedTaskService` (mirrors struct type) |
| Echo / HTTP test scaffolding | `e` (Echo), `req`, `rec`, `context` (never `c`, never `ctx` for the test context — `ctx` is fine for a `context.Context`) |
| Table-driven slice | `tests` (always plural) |
| Row variable | `tc` (test case) |
| Table row name field | `name` |
| Async wait channel | `wait := make(chan any)` |

Type assertions on errors use **hard casts** (no comma-ok) — the test wants to fail loudly if the type is wrong:

```go
echoError := err.(*echo.HTTPError)
```

---

## 7. Mocking — hand-rolled function-field structs

There is no mocking framework. Mocks are file-local structs whose fields are function values matching the interface signatures.

### Anatomy

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

Rules:
- Struct name: lowercase `mocked<InterfaceName>`. Defined at the top of the `_test.go` file, immediately under imports.
- One field per method, named `<methodNameLowerCamel>Func`, typed as a function with the **exact same signature** as the interface method.
- Methods delegate **blindly** to the field — no nil-check, no default return, no recorded call count.
- A test that calls a method whose `*Func` field it never set will nil-panic — that's the convention. Only wire the methods the test exercises.
- Per-test setup uses a struct literal populating only the relevant fields:

```go
mockedTaskService := &mockedTaskService{
    createTaskFunc: func(task *Task) error {
        task.ID = 1
        return nil
    },
}
```

For tests that only need the mock to *exist* (because the code should fail before reaching it), an empty literal is correct: `&mockedTaskService{}`.

### When NOT to mock

If a production-quality in-memory implementation exists, use it. Service-level tests usually wire **zero mocks** — they compose real services with real in-memory repositories. Mocks appear almost exclusively in handler tests to isolate the handler from business logic.

If no in-memory implementation exists yet, fall back to a hand-rolled mock — this is the correct choice, not a violation of the "prefer real" rule.

### Asynchronous code

For callbacks/goroutines, **synchronise with a channel** — never `time.Sleep`:

```go
wait := make(chan any)
notificationService.Subscribe(TaskCompleted, func(n *notifications.Notification) {
    notificationCount++
    wait <- true
})

service.CreateTask(task)

<-wait // block until the handler has run
```

---

## 8. Table-driven tests

Table rows run inside `t.Run` so failures name the failing case:

```go
func TestUserRoleString(t *testing.T) {
    tests := []struct {
        name     string
        role     UserRole
        expected string
    }{
        {name: "technician", role: Technician, expected: RoleTechnician},
        {name: "manager",    role: Manager,    expected: RoleManager},
    }

    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            // when
            result := tc.role.String()
            // then
            if result != tc.expected {
                t.Errorf("expected %s, got %s", tc.expected, result)
            }
        })
    }
}
```

Rules:
- Slice variable: `tests` (plural). Row variable: `tc` (test case).
- Always include a `name` field in the table struct — it becomes the `t.Run` subtest label.
- Field names: `expected` for expected; input fields use domain names (`role`, `username`).
- Extract `tc.input` into a local variable in `// given` when used more than once.
- Table-driven and explicit `t.Run` blocks can coexist inside one `TestFoo` — use a table for scenarios that share the same shape and explicit `t.Run` for complex setups that don't fit.

---

## 9. Assertions — plain `if` + `t.Errorf`

- Use `t.Errorf` for value mismatches (test continues, all failures reported).
- Use `t.Fatalf` / `t.Fatal` only when continuing would crash (nil-pointer dereference, setup failure).
- **No `assert.X` calls** — the package isn't imported.

### Standard message templates

Use verbatim — they're the consistent style:

| Situation | Template |
|---|---|
| Value mismatch | `"expected <name> %v, got %v"` → e.g. `"expected task summary %s, got %s"` |
| Unexpected error | `"unexpected error: %v"` or `"expected no error, got %v"` |
| Missing expected error | `"expected error, got nil"` |
| Wrong status code | `"expected status code %d, got %d"` |
| Substring check | `if !strings.Contains(s, "...") { t.Errorf("expected ... to contain '...', got %s", s) }` |
| Count mismatch | `"expected N <thing>, got %d"` |
| Field is zero / unset | `"expected task ID to be set, got 0"` |
| Wrapped error check | `if !errors.Is(err, target) { t.Errorf("expected errors.Is(%v), got %v", target, err) }` |

Lowercase ("expected …, got …") by default; match the prevailing style of the file you're editing.

---

## 10. HTTP handler tests — canonical recipe

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

        user := &users.User{ID: 1, Username: "alice", Role: users.Technician}
        security.SetAuthenticatedUser(context, user)
        // when
        err := handler.CreateTask(context)
        // then
        if err != nil {
            t.Errorf("expected no error, got %v", err)
        }
        if rec.Code != http.StatusCreated {
            t.Errorf("expected status code %d, got %d", http.StatusCreated, rec.Code)
        }

        var taskResponse TaskResponse
        if err := json.Unmarshal(rec.Body.Bytes(), &taskResponse); err != nil {
            t.Errorf("expected no error parsing response, got %v", err)
        }
        if taskResponse.ID != 1 {
            t.Errorf("expected task ID 1, got %d", taskResponse.ID)
        }
    })
}
```

Conventions:
1. Build the mocked service first, populating only the function fields the test exercises.
2. Wire HTTP scaffolding via the project's helpers (`tests.SetupEcho()`, etc.) — never inline `echo.New()` when helpers fit.
3. For authenticated routes, inject the user via the project's helper. For unauthorized tests, **omit** this call.
4. Invoke the handler method **directly** — do not route through the framework's mux.
5. Assert in this order: returned `err`, status code, body (decoded JSON or full string).
6. For error paths, cast the error and inspect its fields:

```go
echoError := err.(*echo.HTTPError)
if echoError.Code != http.StatusUnauthorized { ... }
```

---

## 11. Service-level tests — canonical recipe

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
        if err != nil {
            t.Fatalf("expected no error, got %v", err)
        }
        savedUser, err := userService.UserByUsername(user.Username)
        if savedUser != user {
            t.Fatalf("expected user to be saved, got %v", savedUser)
        }
    })
}
```

Conventions:
- Compose with the **real** in-memory repository, not a mock.
- Verify side effects by calling another public method (read back what you just wrote) — not by reaching into the repo's internals.
- Domain errors are exposed as exported sentinels; tests compare with `==` (or `errors.Is` if the project uses wrapping):

```go
if err != ErrDuplicatedUsername {
    t.Fatalf("expected ErrDuplicatedUsername, got %v", err)
}
```

---

## 12. Boundary (DTO mapping) tests

```go
func TestToTask(t *testing.T) {
    // given
    user := &users.User{ID: 1, Username: "alice", Role: users.Technician}
    request := &TaskCreateRequest{Summary: "Onboarding call"}
    // when
    task := request.toTask(user)
    // then
    if task.Summary != request.Summary {
        t.Errorf("expected task summary %s, got %s", request.Summary, task.Summary)
    }
    if task.Assignee.ID != user.ID {
        t.Errorf("expected task assignee ID %d, got %d", user.ID, task.Assignee.ID)
    }
}
```

- Test the unexported helper directly (same-package).
- One assertion per mapped field. Don't fold into a deep-equal.
- Don't add roundtrip asserts unless production code does both directions.

---

## 13. Context

Use `t.Context()` (requires Go 1.21+) — it is cancelled automatically when the test and its subtests finish.

```go
// Correct
result, err := service.GetWithContext(t.Context(), "key")

// Wrong — unbounded context leaks past the test
result, err := service.GetWithContext(context.Background(), "key")
```

Reserve `context.WithTimeout` / `WithCancel` only for tests that specifically exercise timeout or cancellation behaviour, and always derive from `t.Context()`:

```go
ctx, cancel := context.WithTimeout(t.Context(), 5*time.Millisecond)
defer cancel()
_, err := service.FetchWithContext(ctx)
if !errors.Is(err, context.DeadlineExceeded) {
    t.Errorf("expected DeadlineExceeded, got %v", err)
}
```

---

## 14. Concurrency tests

Use a named constant for the goroutine count and `sync.WaitGroup` to synchronise:

```go
func TestSyncMapConcurrentSet(t *testing.T) {
    // given
    const goroutines = 100
    m := NewSyncMap[string, int]()
    var wg sync.WaitGroup
    // when
    for i := range goroutines {
        wg.Add(1)
        go func(v int) {
            defer wg.Done()
            m.Set(fmt.Sprintf("k%d", v), v)
        }(i)
    }
    wg.Wait()
    // then
    if m.Len() != goroutines {
        t.Errorf("expected %d entries, got %d", goroutines, m.Len())
    }
}
```

Run with `go test -race ./...` to catch data races.

---

## 15. Nil-safety tests

Types that document nil-safe behaviour must have a dedicated test exercising every nil-safe operation:

```go
func TestSetNilSafety(t *testing.T) {
    // given
    var s Set[int]
    // then
    if s.Len() != 0 {
        t.Errorf("expected Len 0, got %d", s.Len())
    }
    if s.Contains(1) {
        t.Error("expected Contains to return false on nil Set")
    }
    if slice := s.ToSlice(); len(slice) != 0 {
        t.Errorf("expected empty ToSlice, got %v", slice)
    }
    s.Remove(1) // must not panic
}
```

---

## 16. Features explicitly NOT used

Do not introduce without a strong reason:

- testify, go-cmp, or any external assertion library.
- `time.Sleep` for async synchronisation — use `chan any` (see §6).
- `testing.T.Parallel()` — unless the project explicitly adopts it.
- `gomock` / `mockgen` — hand-roll mocks (see §6).
- Separate `TestFooWithCondition` top-level functions — use `t.Run` inside `TestFoo` instead.

---

## 17. Quick checklist for a new test

- [ ] File `<source>_test.go`, next to production file, same package.
- [ ] One top-level `Test<Func>` per function; scenarios go in `t.Run` or table rows (§3).
- [ ] Body structured as given/when/then; add `// given`, `// when`, `// then` comments only if the project already uses them.
- [ ] Only `testing` plus stdlib (and project helpers); no mock library.
- [ ] If a mock is needed: hand-rolled `mocked<Iface>` struct of `…Func` fields at top of file.
- [ ] If an in-memory production implementation exists: use it instead of a mock.
- [ ] Async results awaited via `chan any`, never `time.Sleep`.
- [ ] Assertions: `if … { t.Errorf(…) }` (or `t.Fatalf` only where continuing would crash).
- [ ] Error message templates from §8.
- [ ] Table rows wrapped in `t.Run(tc.name, ...)` — no flat loops.
- [ ] No testify, no go-cmp.
