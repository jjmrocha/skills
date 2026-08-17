---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing production code. Triggers on "implement X", "add feature Y", "fix bug Z", "build a function that…", or when about to write production code without a failing test.
---

# Test-Driven Development

Write the test first. Watch it fail. Write minimal code to pass. Clean up. Repeat.

Tests written *before* code specify what to build. Tests written *after* only confirm what you already built. The order is the whole point.

## The Cycle

```
RED → GREEN → REFACTOR → repeat
```

### RED — Write a failing test

Write one test for the next behavior. Use the API you wish existed.

**Gate:** Run it. It must fail for the *right* reason (function doesn't exist, assertion on expected behavior) — not a syntax error. If it passes, you're testing existing behavior; rewrite.

**REQUIRED SUB-SKILL:** Invoke `writing-unit-tests` before writing the test — scenario selection, naming, structure. Do not write test code without it.

### GREEN — Write minimum code to pass

The smallest thing that makes the test pass. Not clever, not general — minimal. Every line beyond what the test requires is scope creep.

See `coding-discipline` — the scope creep and speculative complexity failure modes apply directly.

**Gate:** Full suite green. Every test, not just the new one.

### REFACTOR — Clean up without adding behavior

Change *how*, not *what*.

Walk each item and report one line for it — what you changed, or "already clean":

- **Duplication** — the same knowledge expressed in two places
- **Naming** — does each name say what it is, not how it works?
- **Cognitive complexity** — nesting depth, branch count, boolean operators per condition. Extract until the function reads top-to-bottom in one screen.
- **Single responsibility** — does this function do one thing?
- **No side effects** — mutation of arguments, globals, or receiver state that the name doesn't advertise
- **Dead code and speculative generality** — delete it

For significant structural changes, load the `refactoring-expert` specialist from `using-software-specialists`.

**Gate:** the six lines above, then the suite green. Then write the next failing test.

## Adapting to Existing Code

| Situation | What to do |
|-----------|------------|
| **New behavior in existing code** | Write failing test for new behavior first, then implement |
| **Bug fix** | Write a test that reproduces the bug, watch it fail, then fix. The test stays as a regression guard. |
| **Refactoring existing code** | Characterize current behavior with tests first. Run them green on unmodified code. Then refactor with the suite as your safety net. |
| **Starting fresh** | Write the test before any production code |

## Scenarios Where TDD Feels Hard

| Excuse | Reality |
|--------|---------|
| "I don't know the right interface yet" | That's a signal. Write the test using the interface you wish existed. If the test is awkward to write, the interface is awkward to use. |
| "This is a UI / infrastructure / glue code" | Adapt the grain, not the order. UI: test observable state. Infra: test the interface contract. Glue: test the wiring. |
| "The existing code has no tests" | Characterize with tests first — that's your baseline. Then modify. |
| "Too simple to need a test" | A 3-line test costs less than the future debugging session. |
| "Tests after achieve the same purpose" | Tests-after confirm. Tests-before specify. Fundamentally different. |
| "This will slow me down" | TDD is faster than: write → manually test → find bug → debug → fix → re-test. |

## Red Flags — Stop and Start Over

- Code before test
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "This is different because..."
- "I'll add tests before the PR"

All of these mean: write the failing test, start over.