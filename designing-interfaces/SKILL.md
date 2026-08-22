---
name: designing-interfaces
description: Use when writing or changing code other code will call — a new type, function, method, module, or package — before the implementation exists. Also when a caller needs data or behavior a module does not currently expose, when widening an existing interface, adding a getter, or deciding where new logic should live.
---

# Designing Interfaces

**A zero-line diff is not a zero-cost change.** The cheapest change to write is usually the one that moves complexity out to the callers, where no diff records it.

An **interface** here is everything a caller must know to use a module correctly: the signature, plus the types it drags along, the constants, the ordering rules, the error modes, and the invariants. Not just the type-level surface.

## The Contract

**REQUIRED: write this before the implementation. Four lines. Put it in your reply, not in a comment.**

```
CALLER LEARNS:  <every type, constant, and rule the caller must know — list them, don't summarize>
HIDDEN:         <the behavior the module performs on the caller's behalf>
SEAM:           <where the interface sits, and what varies across it>
TEST CALLS:     <the exact entry point the test will use>
```

Then read it back:

- **HIDDEN is empty or one clause** → the module is shallow. It is a conduit, not a module. Redesign before writing code.
- **CALLER LEARNS is longer than HIDDEN** → you moved complexity to the callers. Redesign.
- **TEST CALLS names something not in CALLER LEARNS** → the test reaches past the interface. Either the entry point is wrong, or the module is.

**Thin by design.** A registration, adapter, or dispatcher whose depth lives behind the
interface it *calls* is supposed to be thin. Its HIDDEN slot names what that callee hides,
and points at it. If you cannot name the callee, HIDDEN is genuinely empty and the rule
above applies — "it's just a conduit" is only true when you can say what it is a conduit to.

The contract is cheap on purpose. Four lines is not a design document; it is the smallest thing that makes interface width visible before you have paid for the implementation.

### Worked example

A command needs the conversation transcript, which the core holds privately.

```
✗ CALLER LEARNS:  Line{Kind,Text}, Kind, its 6 constants, that the slice is a snapshot copy
  HIDDEN:         nothing — it returns stored state
  SEAM:           none; the command calls os.WriteFile directly
  TEST CALLS:     an unexported render function, plus a real temp directory
```

Ten facts learned, zero behavior hidden — and `Kind`'s six constants now belong to every
caller forever. HIDDEN is empty, so stop.

```
✓ CALLER LEARNS:  SaveTranscript(path string) (resolved string, err error);
                  empty path means "pick a default"
  HIDDEN:         locking, rendering, filename defaulting, writing, file mode
  SEAM:           the core's own interface; the fake core is the second adapter
  TEST CALLS:     SaveTranscript
```

Two facts learned, five behaviors hidden. The transcript's representation never escapes.

## Interface width is a cost

Adding a method to an interface is a cost **even when no implementation changes.** An
existing type that already satisfies the new method has not made the change free — it has
hidden the price. What you actually changed is the set of things every caller may now do
and every future implementer must provide.

Price it by asking what the *widest* caller can now reach, not how many lines you edited.

Two more checks on the finished contract:

- **Deletion test.** Delete the module. If complexity vanishes, it was a pass-through and should not exist. If it reappears in N callers, it earned its place.
- **Accept dependencies, don't construct them.** A module that builds its own I/O, clock, or client has no seam, and its tests will reach around it.

## Seams

A **seam** is a place you can change behavior without editing in that place.

Introduce one only when something actually varies across it. **The test counts as the
second adapter when — and only when — the dependency is I/O, a clock, randomness, or the
network.** For those, "only one caller exists" is not a reason to skip the seam; the test
is the other caller, and without the seam the test reaches around the module instead of
through it.

For anything else — pure computation, in-process state — one caller means no seam. Call it
directly.

## Relationship to coding-discipline

`coding-discipline` minimizes **what you build**. This skill constrains **what you expose**.
They pull in opposite directions exactly once, and this is the case that matters:

> The shallow design is almost always the smaller diff.

When the two conflict, minimality applies to the implementation, never to the caller's
required knowledge. "Could a senior cut this in half?" is a question about the
implementation. A smaller diff that widens an interface is not the smaller change.

`coding-discipline`'s speculative-complexity test — *does a second caller exist right now?* —
governs parameters, flags, and configuration. It does not govern seams at I/O boundaries;
the Seams rule above does.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The type already has this method, so the interface change is free" | You changed what every caller may do and every implementer must provide. Zero diff, real cost. |
| "The core still owns the state" | It owns the field. If callers read it directly, they own the representation, and you can never change it. |
| "It's still a narrow surface" | Count the facts in CALLER LEARNS. Say the number. |
| "I'll expose the state and let the caller decide policy" | Then policy lives in N callers. Name the second caller that wants a different policy — if there isn't one, the policy belongs inside. |
| "A type alias means nothing breaks" | Aliases hide dependency-direction changes. Which package owns the type now? |
| "One caller doesn't justify inventing an abstraction" | True for parameters. False for I/O, clocks, and randomness — the test is the second caller. |
| "It's technically breaking but the blast radius is nil" | You priced it and then discarded the price. Put the number in the contract instead. |
| "The tests pass and the linter is clean" | Neither one can see interface width. That is why the contract exists. |
| "I'll just add a getter" | A getter hides nothing. HIDDEN is empty. |

## Red Flags

- Writing a method that only returns stored state to a caller outside the module
- Moving a type into another package so an interface will compile
- Reaching for a type alias to keep existing code building
- A test that calls an unexported function, or touches a real filesystem, clock, or network
- "…so it satisfies the interface with no new code"
- Formatting or rendering a module's private representation from outside that module
- Noting a cost in your summary and then proceeding anyway

**All of these mean: write the contract, and read HIDDEN.**
