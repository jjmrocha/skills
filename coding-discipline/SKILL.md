---
name: coding-discipline
description: Use when writing or modifying code, especially in agentic flows — before composing diffs, generating new modules, or applying suggested fixes
---

# Coding Discipline

**If you can name the failure mode you're about to commit, you usually won't commit it.**

Six failure modes most common in LLM-written code, with the counter for each.

## The Six Failure Modes

| Failure mode | Symptom | Counter |
|--------------|---------|---------|
| **Silent assumption** | Picking one reading of an ambiguous ask | State the assumption, or ask |
| **Scope creep** | Touching adjacent code "while here" | Every changed line traces to the ask |
| **Speculative complexity** | Adding config/abstraction nobody asked for | Build the smallest thing |
| **Hallucination** | Referencing symbols/APIs/paths that don't exist | Verify before writing; run before claiming done |
| **Drift** | Losing the original goal over a long session | Stop when the verifiable check passes |
| **Parallel solution** | New helper/pattern for a problem the repo already solves | Search first; reuse what exists |

## Falsifiable Tests

**Silent assumption.** Before any non-trivial change, name the load-bearing assumption in one sentence. If you can't, you don't know what you're building. If two readings are reasonable, present both — e.g., *"Reading 'cache user lookups' as in-process LRU rather than shared cache — flag if you meant the latter."*

**Scope creep.** A diff answers one question: *what did the user ask for?* Every other line is contraband. Allowed: orphans your own change created (unused imports, dead branches you rewrote). Not allowed: "while I'm here" reformatting, renaming, dead-code removal, style sweeps — mention them in your reply, don't commit them. Two unrelated chunks → split the diff.

**Speculative complexity.** *Does a second caller exist right now that needs a different value?* No → don't add the parameter. The same test kills: "I'll make this configurable", base classes for hypothetical implementations, wrappers for hypothetical callers, and handling structurally impossible errors. If the simplest version is half the size, write that one.

**Hallucination.** Look it up before writing — prefer serena symbolic tools (`find_symbol`, `get_symbols_overview`, `find_referencing_symbols`) over `Read`/`Grep`; context7 for external library docs; `grep`/`Read` otherwise. *"It should work"* ≠ *"I ran it and it works"*. When you couldn't confirm, mark uncertainty: *"I think it's `obj.foo()` but haven't verified."*

**Drift.** Restate the request as one of: a failing test you'll make pass, a specific output you'll produce, a specific observable behavior. For multi-step work: 2–4 steps, each paired with its check. A step is done when its check passes — not before.

**Parallel solution.** Before writing a new helper, pattern, or solution, ask: *does this codebase already solve this problem class?*
- **Pattern:** pagination/validation/auth/error-handling/retries/logging/config — find an existing one and copy its shape.
- **Helper:** before writing `formatDate`/`chunk`/`parseId`, grep for similar names and inspect existing utils modules.
- **Library:** before adding a dependency, check `package.json` / `go.mod` / `pyproject.toml` for an existing equivalent.

Parallel solutions double maintenance, split conventions, and confuse future readers about which version is canonical.

## Pre-Commit Self-Check

1. **Assumption** — stated, or "n/a"?
2. **Scope** — every changed line traces to the request?
3. **Simplicity** — could a senior cut this in half?
4. **Verification** — confirmed referenced symbols/APIs exist? Ran the code, not just wrote it?
5. **Goal** — can you name the check that proves this is done?
6. **Reuse** — checked the codebase for an existing solution (helpers, patterns, libraries)?

A "no" on any line: stop and revise; don't ship and explain.

## Red Flags

| Inner thought | What it means |
|---------------|---------------|
| "I'll just guess what they meant" | Surface the assumption |
| "While I'm here, let me also…" | Scope creep — stop |
| "Let me add a flag for flexibility" / "That's real flexibility, not speculation" | No second caller exists → don't add the parameter |
| "I'll handle every conceivable error" | Many are structurally impossible |
| "I'm pretty sure that method exists" / "It should work" | Hallucination — look it up; run before claiming done |
| "I lost track of what they wanted" | Drift — restate the goal |
| "I'll just write a quick helper" / "I'll add a library for this" | Grep first; the repo may already solve it |

For trivial tasks (typo fix, one-line rename), use judgment — this skill biases toward caution.
