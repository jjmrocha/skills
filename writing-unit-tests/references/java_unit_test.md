# Java Unit Test Reference

Prescriptive guide for writing unit tests in Java. Following it produces tests that read consistently and follow the universal principles in `SKILL.md`.

**Stack**: JUnit Jupiter 5+ • AssertJ • Mockito. No Hamcrest. No PowerMock. No JUnit 4.

> **Always check the project's existing tests first.** If they differ from this reference (different assertion library, different mock style, `@Mock` annotations, etc.), follow them. This reference is the default for greenfield code.

This reference follows the **FIRST-U** principles (Fast, Isolated, Repeatable, Self-validating, Timely, Understandable) defined in §4 of the main skill. Every test here should satisfy each letter.

---

## 1. Dependencies

```kotlin
// build.gradle.kts — example
testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
testImplementation("org.assertj:assertj-core:3.27.3")
testImplementation("org.mockito:mockito-core:5.20.0")
testRuntimeOnly("org.junit.platform:junit-platform-launcher")

// Required if you need to mock final classes/methods or statics:
mockitoAgent("org.mockito:mockito-core:5.20.0") { isTransitive = false }
tasks.test {
    jvmArgs("-javaagent:${mockitoAgent.singleFile.absolutePath}")
    useJUnitPlatform()
}
```

Do not add Mockito JUnit extension, Hamcrest, or PowerMock unless the project already uses them.

---

## 2. File layout

Tests mirror the production package, one test class per production class:

```
src/main/java/com/example/order/OrderService.java
src/test/java/com/example/order/OrderServiceTest.java
```

- Test class name: `<ClassUnderTest>Test`.
- Same package as the class under test, giving package-private access.

---

## 3. What to test, by layer

| Layer | Mock | Don't mock | Focus |
|-------|------|------------|-------|
| **Controllers (`@RestController`)** | Service layer | — | `@Valid` payload validation, auth, response status/body |
| **Services (`@Service`)** | Repository interface | Internal pure modules | Business logic: given state + inputs, verify outputs |
| **Builders / mappers** | Nothing | Everything | Input → output mapping. Parameterized tests. |
| **External clients** | `MockWebServer` (OkHttp) — not the SDK directly | — | Request shape (method, URL, headers) and every response branch |
| **Event listeners** | Bus / broker interface | — | Payload schema, behavior on valid/malformed/duplicate events |

---

## 4. Class and method modifiers

Test classes and test methods are **package-private** — no `public`, no `protected`.

```java
class OrderServiceTest {
    @Test
    void testCreateOrder() { ... }
}
```

Helper methods are `private static` unless they need instance state.

---

## 5. Canonical variable names

These are the names every test should use. Consistency makes the codebase scannable.

| Variable        | Meaning                                                                |
|-----------------|------------------------------------------------------------------------|
| `classUnderTest`| The instance whose behavior is being tested. Always this name. |
| `result`        | The return value of the method under test (the "when" output).         |
| `expected`      | The expected value compared against `result`, when it needs a name.    |

Do not use `sut`, `underTest`, `subject`, `actual`, `output`, or domain-specific names like `service`. Use exactly these names so any reader recognizes the pattern instantly.

---

## 6. Given / When / Then structure

Every test uses three lowercase comments to delimit phases:

```java
@Test
void testParseDateWithIsoFormat() {
    // given
    var classUnderTest = new DateParser();
    var input = "2024-03-15";
    // when
    var result = classUnderTest.parse(input);
    // then
    assertThat(result).isEqualTo(LocalDate.of(2024, 3, 15));
}
```

Rules:
- Write `// given`, `// when`, `// then` markers **only if the existing project tests already use them**; if they don't, keep the same three-block structure without comments.
- When used, always lowercase, no colons: `// given`, `// when`, `// then`.
- **`// when` is one statement** — the call to the unit under test (plus `result = ...`).
- **`// then` holds all assertions.**
- Omit `// given` only when class-level fields already supply the setup.
- For void methods, `// when` invokes the action and `// then` inspects side effects.

---

## 7. Test method naming

Format: **`test` + PascalCase description**, no underscores, no `@DisplayName`.

```java
void testParseDateWithIsoFormat()        // ✅ method + scenario
void testProcessRejectsInvalidPayload()   // ✅ method + behavior
void testWithdrawWhenBalanceIsZero()      // ✅ state-based scenario
void testOk()                             // ✅ short factory method

void testParseDate_WithIsoFormat()        // ❌ underscores
void shouldParseIsoFormat()               // ❌ `should` prefix
void parse_date_iso()                     // ❌ snake_case
```

Guidelines:
- Start with the method under test, PascalCased.
- Add a scenario clause: `With...`, `When...`, or a verb like `Rejects...`/`Returns...`.
- For factories/builders, the method name alone is fine (`testOk`, `testEmpty`).
- Never `@DisplayName` — the method name is the description.

---

## 8. Imports

Prefer `var` for locals. AssertJ and Mockito are imported statically.

```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.AssertionsForClassTypes.catchThrowable;

import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import org.mockito.MockedStatic;
```

Note: when a test class *only* asserts on enums, use `org.assertj.core.api.AssertionsForClassTypes.assertThat` (it has the enum-aware overload). Otherwise default to the standard `Assertions.assertThat`.

---

## 9. Fixtures and helpers

Initialize stateless or cheap collaborators as `private final` fields:

```java
class OrderServiceTest {
    private final OrderRepository orderRepository = new InMemoryOrderRepository();
    private final OrderService classUnderTest = new OrderService(orderRepository);
}
```

When `classUnderTest` is a field, individual tests omit creating it in `// given` and refer to the field directly.

Use `@BeforeEach`/`@AfterEach` only when lifecycle setup is needed (e.g., opening/closing a `MockedStatic`). Do **not** use `@BeforeAll`/`@AfterAll`.

### Helper methods — `build*` prefix

Private static helpers build fixtures. Name them `build<Thing>` and return the fully constructed object:

```java
private static Order buildOrder(String customerId, BigDecimal total) {
    return new Order(customerId, total, Status.PENDING);
}

private static HttpRequest buildHttpRequest(String method, String url) {
    return new HttpRequestImpl(method, url, Map.of(), null);
}
```

Helpers may include `assertThat(...)` calls to fail fast on setup errors.

---

## 10. The `isInstanceOf` + cast idiom

When a method under test returns an **interface** but you need to assert on the concrete implementation's state, follow this pattern:

```java
@Test
void testOk() {
    // when
    var result = HttpResponse.ok();
    // then
    assertThat(result).isInstanceOf(HttpResponseImpl.class);
    var impl = (HttpResponseImpl) result;
    assertThat(impl.getStatusCode()).isEqualTo(200);
    assertThat(impl.getBody()).isNull();
}
```

Even when `classUnderTest` is named only inside `// then`, keep the same variable name.

---

## 11. Time and randomness

Determinism is non-negotiable. Pin both via injection or `MockedStatic` (see §15):

```java
// Pinning time: inject a fixed Clock (preferred — no mocking needed)
var fixedClock = Clock.fixed(Instant.parse("2024-01-15T12:00:00Z"), ZoneOffset.UTC);
var classUnderTest = new OrderService(fixedClock, orderRepository);
```

For randomness, inject a `java.util.Random` with a fixed `seed` rather than calling `Math.random()`:

```java
var rng = new Random(42);
var classUnderTest = new TokenGenerator(rng);
```

This guarantees the same sequence every run. Without it, tests fail **Repeatable** from SKILL.md §4.

---

## 12. Passing `null` for irrelevant arguments

When a constructor takes parameters the test does not care about, pass `null` rather than creating throwaway fixtures:

```java
// Request(HttpMethod, String url, Headers headers, String body, boolean keepAlive)
var request = new Request(HttpMethod.GET, "/api", null, null, false);
```

Only populate fields the test observes or exercises. Keeps `// given` focused.

---

## 13. AssertJ — catalogue

Prefer the most specific method for the type.

### Equality, identity, null

```java
assertThat(result).isEqualTo(expected);
assertThat(result).isSameAs(otherRef);
assertThat(result).isNull();
assertThat(result).isNotNull();
```

### Booleans and numerics

```java
assertThat(flag).isTrue();
assertThat(flag).isFalse();
assertThat(count).isZero();
assertThat(elapsed).isGreaterThanOrEqualTo(100);
assertThat(elapsed).isLessThan(50);
```

### Strings

```java
assertThat(result).isEqualTo("expected");
assertThat(throwable).hasMessage("Exact message.");
assertThat(throwable).hasMessageContaining("substring");
```

### Collections

```java
assertThat(list).isEmpty();
assertThat(list).hasSize(3);
assertThat(list).containsExactly("a", "b", "c");                 // order matters
assertThat(list).containsExactlyInAnyOrder("a", "b", "c");       // order does not matter
```

### Maps

```java
assertThat(map).containsEntry("key", "value");
assertThat(map).containsKey("key");
assertThat(map)
        .containsEntry("k1", "v1")
        .containsEntry("k2", "v2")
        .hasSize(2);
```

### Chaining

Chain while the subject does not change. Start a new `assertThat(...)` when the subject changes.

---

## 14. Exception testing — `catchThrowable`

Do **not** use `assertThatThrownBy`. Use `catchThrowable`, then assert on the caught throwable:

```java
@Test
void testWithdrawRejectsInsufficientBalance() {
    // given
    var classUnderTest = new Account(BigDecimal.valueOf(50));
    // when
    var result = catchThrowable(() -> classUnderTest.withdraw(BigDecimal.valueOf(100)));
    // then
    assertThat(result).isInstanceOf(InsufficientBalanceException.class);
    assertThat(result).hasMessage("Withdrawal exceeds balance.");
}
```

- The caught value is still named `result`.
- Use `.hasMessage(...)` for exact match, `.hasMessageContaining(...)` for substring.

---

## 15. Parameterized tests

Use `@ParameterizedTest` + `@MethodSource` with a private static factory returning `Stream<Arguments>`.

```java
@ParameterizedTest
@MethodSource("httpMethods")
void testFromString(String value, HttpMethod expected) {
    // when
    var result = HttpMethod.fromString(value);
    // then
    assertThat(result).isEqualTo(expected);
}

private static Stream<Arguments> httpMethods() {
    return Stream.of(
            // value, expected
            Arguments.of("invalid", null),
            Arguments.of("get", HttpMethod.GET),
            Arguments.of("GET", HttpMethod.GET),
            Arguments.of("post", HttpMethod.POST)
    );
}
```

Rules:
- Source method goes at the **bottom** of the class.
- The first line of `Stream.of(...)` carries a comment listing the argument names in order. Non-negotiable — it's what makes the table readable.
- Source name describes the inputs (`httpMethods`, `parseInputs`) or, for matrices, `<thing>Combinations`.
- Prefer `@MethodSource` over `@CsvSource` / `@ValueSource` / `@EnumSource` — all parameter sources live with the test class.

---

## 16. Mockito

### Mocking instances

Use `mock(Class)` programmatically. Configure with BDD style — `given(...).willReturn(...)`, not `when(...).thenReturn(...)`.

```java
var orderRepository = mock(OrderRepository.class);
given(orderRepository.findById("ord-1")).willReturn(Optional.of(buildOrder("cust-1", BigDecimal.TEN)));
```

Do **not** use `@Mock`, `@InjectMocks`, or `@ExtendWith(MockitoExtension.class)`.

### Mocking statics

Use `MockedStatic` opened in `@BeforeEach` and closed in `@AfterEach`:

```java
private MockedStatic<LocalDate> mockedNow;

@BeforeEach
void setUp() {
    mockedNow = mockStatic(LocalDate.class);
    mockedNow.when(LocalDate::now).thenReturn(LocalDate.of(2024, 1, 15));
}

@AfterEach
void tearDown() {
    mockedNow.close();
}
```

Name the field after what's mocked: `mockedClock`, `mockedNow`, etc.

### Don't `verify` unless interaction is the contract

The codebase asserts via observable state, not call counts. Reach for `verify(...)` **only** when the call itself is the contract (e.g., "did we send the confirmation email?"). For everything else, assert the return value or resulting state.

---

## 17. Async tests

JUnit 5 supports `CompletableFuture` directly with `Awaitility` or by joining in a plain `@Test`:

```java
@Test
void testFetchReturnsPayload() throws Exception {
    // given
    var classUnderTest = new AsyncFetcher(Duration.ofSeconds(1));
    // when
    var result = classUnderTest.fetch("/health").get(2, TimeUnit.SECONDS);
    // then
    assertThat(result.getStatus()).isEqualTo(200);
}
```

For reactive pipelines (Project Reactor, RxJava), block on the publisher:
- Reactor: `StepVerifier.create(flux).expectNext(...).verifyComplete()`
- Always set a timeout — the test must fail fast if the async operation hangs.

---

## 18. Features explicitly NOT used

Do not introduce without a strong reason:

- `@DisplayName`
- `@Nested` classes
- `@BeforeAll` / `@AfterAll`
- `@Disabled`, `@Tag`, `@Timeout`, `@RepeatedTest`
- `@Mock`, `@InjectMocks`, `@Captor`, `@ExtendWith(MockitoExtension.class)`
- `Mockito.verify(...)` for non-side-effect calls
- `assertThatThrownBy` (use `catchThrowable`)
- `when(...).thenReturn(...)` (use `given(...).willReturn(...)`)
- Hamcrest
- `public` modifier on test classes/methods
- `@CsvSource` / `@ValueSource` / `@EnumSource` (use `@MethodSource`)

---

## 19. Skeleton

```java
package com.example.order;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.AssertionsForClassTypes.catchThrowable;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;

class OrderServiceTest {
    private final OrderRepository orderRepository = mock(OrderRepository.class);
    private final OrderService classUnderTest = new OrderService(orderRepository);

    @Test
    void testCreateOrderPersistsOrder() {
        // given
        var input = buildOrder("cust-1", BigDecimal.TEN);
        given(orderRepository.save(input)).willReturn(input.withId("ord-1"));
        // when
        var result = classUnderTest.create(input);
        // then
        assertThat(result.getId()).isEqualTo("ord-1");
        assertThat(result.getStatus()).isEqualTo(Status.PENDING);
    }

    @Test
    void testCreateOrderRejectsZeroTotal() {
        // given
        var input = buildOrder("cust-1", BigDecimal.ZERO);
        // when
        var result = catchThrowable(() -> classUnderTest.create(input));
        // then
        assertThat(result).isInstanceOf(InvalidOrderException.class);
        assertThat(result).hasMessage("Order total must be positive.");
    }

    private static Order buildOrder(String customerId, BigDecimal total) {
        return new Order(customerId, total, Status.PENDING);
    }
}
```

---

## 20. Quick reference

| Task                              | How                                                                    |
|-----------------------------------|------------------------------------------------------------------------|
| Test annotation                   | `@Test`                                                                |
| Parameterized test                | `@ParameterizedTest` + `@MethodSource("name")`                         |
| Lifecycle                         | `@BeforeEach` / `@AfterEach` only                                      |
| Class / method modifier           | Package-private                                                        |
| Subject-under-test variable       | `classUnderTest`                                                       |
| Result variable                   | `result`                                                               |
| Default assertion import          | `static org.assertj.core.api.Assertions.assertThat`                    |
| Exception import                  | `static org.assertj.core.api.AssertionsForClassTypes.catchThrowable`   |
| Exception test                    | `var result = catchThrowable(() -> ...); assertThat(result)...`        |
| Equality                          | `assertThat(x).isEqualTo(y)`                                           |
| Type check                        | `assertThat(x).isInstanceOf(Foo.class)`                                |
| Ordered collection                | `assertThat(list).containsExactly(...)`                                |
| Unordered collection              | `assertThat(list).containsExactlyInAnyOrder(...)`                      |
| Throwable message exact           | `.hasMessage("...")`                                                   |
| Throwable message substring       | `.hasMessageContaining("...")`                                         |
| Mock creation                     | `mock(ClassName.class)`                                                |
| Mock stubbing                     | `given(mock.method()).willReturn(value)`                               |
| Static mock                       | `mockStatic(ClassName.class)` — closed in `@AfterEach`                 |
| Helper method naming              | `build<Thing>`, `private static`                                       |
