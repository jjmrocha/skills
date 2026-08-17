---
name: guiding-manual-testing
description: Use when the user asks for help testing a change by hand against real data on a real environment (local or staging), rather than in automated tests — "help me test this on staging", "guide me through testing X", "verify this works on the team env", "how do I test this manually", or when a path they want to check only manifests with production-shaped data.
---

# Guiding Manual Testing — Verification on a Real Environment

Prove a change behaves correctly against real data on a real environment. The user is the hands: the agent proposes exactly one action, the user runs it and pastes the output, the agent interprets it and proposes the next. Nothing is asserted that was not observed.

**If the conversation was compacted, re-invoke this skill before continuing.**

## When NOT to Use

| Situation | Instead |
|---|---|
| Writing automated tests | `test-driven-development` / `writing-unit-tests` |
| Auditing the code itself | `analyze-code` |
| Answering "how does X work" from the code | `research` |
| Production environment | Not supported — local, testing or staging only |

## Hard Rules

1. **Name the environment first.** Before Phase 1, state which environment this runs against and have the user confirm it — local, testing or staging, and which one. Never infer it from a config file you happen to see. If the user names production, stop: not supported.
2. **One step per message.** A single action, then wait. Never a numbered list of five steps, never a branch tree of "if X then... else...". The next step is not knowable until the current output is read.
3. **Matched pair required.** A verification passes only when *both* the case that must change and the case that must not have been observed. A single negative result proves nothing — a query matching nothing produces the identical output. Before reading any negative result, **confirm the trigger actually ran**; a no-op run yields a perfect-looking false negative.
4. **Prefer real creation paths.** Produce data by running the job, using the UI, or calling the endpoint. Direct database mutation is a fallback and must be justified out loud — name the real path and why it is unavailable.
5. **Restore point before direct mutation.** If you mutate data directly, capture and echo back the exact restoring statement before doing so. Data produced by running the real path — the job, the UI, the endpoint — is legitimate system state; leave it in place. State the blast radius of any trigger before running it.
6. **No invented identifiers.** Every table, column, flag, endpoint, menu, and button name in a proposed step must come from something read this session — the schema, a migration, the code (including templates/components for UI labels), or what the user said is on screen. If you haven't read it, make *getting* it the step: ask for `\d <table>`, the predicate from the source file, or what the current screen shows. A guessed name that happens to exist is worse than one that errors — the query runs and answers a different question, and a guessed menu path sends the user hunting.

## Workflow

Each phase's output is stated back to the user before the next begins.

### Phase 1 — Establish intent

What is supposed to change, in one paragraph, naming the specific condition that changed. Sources in priority order:

1. The implementation plan in the KB plans dir — if `kb_path` is configured and one exists (load `knowledge-base`).
2. The spec or ticket the user provided — or one the user names.
3. The diff — `git diff <base>...HEAD`, scoped to the change under test.

Read all that are available; the diff is authoritative when they disagree. Tickets are often empty or stale — say so rather than inferring acceptance criteria that were never written. If none of the three yields intent, ask.

**Output:** the changed condition, stated precisely enough to predict outcomes from. "Batches are now only linked when they have a non-deleted claim whose transaction is already in the statement" is usable. "The query was fixed" is not.

### Phase 2 — Map the path and the triggers

Trace the changed symbol to its callers — serena's `find_referencing_symbols` (`get_symbols_overview` → `find_symbol` to locate it first), or grep for the symbol if serena is unavailable — then out to entry points: CLI job, HTTP route, subscriber, scheduled job, UI action. Then read the **environment's own deployment config** — Helm values, env manifests, compose files — to learn which of those exist on the target environment, on what schedule, and under which feature flags.

**Output:** the trigger options with trade-offs, and a recommendation. Prefer the narrowest trigger that reaches the changed code. A client-scoped or record-scoped entry point beats a global batch job; a global job that already runs nightly beats a flow that rejects and rebuilds unrelated state.

Note environment flags that gate the code path — a feature disabled by config on the target environment makes the test impossible before any data is examined.

### Phase 3 — Feasibility ladder

One rung per message, each a single query. Climb only as far as needed:

1. **Does data of the required shape exist?** Counts and date ranges, not row dumps.
2. **Is the configuration that enables the feature turned on?** Read the gate conditions from the code, then check them in the data — quote the code that requires each flag.
3. **Can the case actually be constructed?** Check the selection predicates of whatever would create the data. They are usually stricter than expected.

**"This environment cannot test this — here is what is missing" is a valid outcome.** Say it plainly rather than forcing a weak test. Report which rung failed and what would have to change.

### Phase 4 — Design the matched pair, and predict

**Prefer a pair that already exists.** If the environment already holds a record satisfying each side, use those — no setup, no mutation, nothing to restore, and the evidence is real data rather than data arranged to pass. Construct a case only when the search comes back empty, and say that it did.

Name both cases and why each qualifies:

- **Must-stay case** — the trigger must leave it untouched. It satisfies every condition the old code required, and fails exactly the one the change added.
- **Must-change case** — the trigger must affect it. It satisfies the new condition too, proving the mechanism still works.

Then **write the predicted outcome of both before anything runs**. Prediction first is what stops a surprising result from being rationalized after the fact. If the two cases cannot be isolated to a single differing condition, the test is not yet designed — keep working on it.

### Phase 5 — Execute

Record the restore point if the setup mutates data directly, then setup (if any) → trigger → observe, one action per message.

Message format:

```
**Step N.** <why this step exists — one sentence>

<one action: a command, a query block, or a UI path — "menu X → Y → click A">

<what to paste back — the output, or what the screen shows after>
```

A UI step is still one action: one screen's worth of clicks toward a single
observable result, not a tour of the flow.

- Interpret the output before proposing the next step. State what it means.
- If the output contradicts the prediction, **stop and re-derive** from the code. Do not improvise forward.
- **Every mutation step ends with a verification read in the same message.** Users frequently execute only the statement under the cursor; a trailing `SELECT` catches it immediately.
- Prefer a mutation and its verification in one step over splitting them; prefer splitting two independent mutations over combining them.

### Phase 6 — Report and restore

Deliver the report in the conversation — do not write it to a file unless asked. Then, if data was mutated directly, restore the recorded state and verify the restore landed. State produced by the real path stays.

Unexpected observations are the most valuable output. A verification that passes and also reveals a consequence nobody planned for has earned more than a green check. Report those as separate findings with their own evidence.

The report is the deliverable. Do not fix what the verification found — this skill observes, it does not change code. Route instead:

- **Verification failed** → `using-software-specialists`, starting with Troubleshooter.
- **A bug was proven** → reproduce it as a failing test first (`test-driven-development`), so the fix has a red test behind it.
- **Unexpected observations** → `analyze-code` if they suggest the change needs a broader audit.

## Report Template

```markdown
# Verification: <feature / ticket>

**Environment:** <local | testing | staging env name>
**Intent source:** <KB plan path | ticket KEY | diff range>
**Under test:** <the condition that changed, one paragraph>

## Test data chosen
<what was used and why it qualifies — including what was ruled out and why>

## Cases

| Case | Setup | Predicted | Observed | Verdict |
|---|---|---|---|---|
| <name> | <what was arranged> | <written before the run> | <evidence> | pass/fail |

## Findings
- <unexpected observation> — <evidence> — <impact> — <suggested fix, with file:line>

## Cleanup
<statements run to restore, and the verified end state — or "none needed: no direct data mutation">
```

## Example: good vs bad step

**Bad** — a plan issued before any data was examined:

```
Step 1 — find a candidate client.
Step 2 — if it has batches, unlink one; if not, enable the toggles and create one.
Step 3 — trigger the job (or the refresh flow if you need client scope).
Step 4 — check the result.
```

Four steps, two branches, all speculative. Steps 2–4 assume facts nobody has checked. When step 1 comes back empty, the whole plan is discarded and the user has read it for nothing.

**Good** — one rung, one query, one thing to paste:

```
**Step 1.** Before anything else, confirm the feature is even enabled for
these clients — the batch job requires three flags to be on
(assertConfigForDailyBatch, claims_batch_creator.go:326-346).

SELECT ... FROM statement_configuration ... WHERE client_id IN (148, 203);

Paste the result.
```

## Red Flags — STOP

| Thought | Reality |
|---------|---------|
| "They asked for all the steps up front" | The next step isn't knowable until this output is read. Give one — the rest would be discarded anyway. |
| "I'll let them branch on the result" | Branching instructions hand your job to the user. Ask for the output and branch yourself. |
| "I can predict how this goes" | Then checking costs nothing. A prediction written after the output is a rationalization. |
| "Nothing came back — the fix works" | A no-op run returns the same empty result. Confirm the trigger ran before reading any negative. |
| "Writing the INSERT is faster than running the job" | Hand-made data can satisfy conditions the real path never produces. Name the real path and why it's unavailable. |
| "That case is obviously unaffected" | Obvious is not observed. Both cases, or no verdict. |
| "I'll capture the restore point once the mutation works" | Restore statement first, or the mutation doesn't run. |
| "The job touches other records, but that's expected" | State the blast radius out loud before the trigger, not after. |
| "They'll run the whole SQL block" | Users execute only the statement under the cursor. Every mutation step ends with a verification read. |
| "The environment is missing X, but we can approximate" | "This environment cannot test this" is a valid, honest outcome. Report the failed rung instead of forcing a weak test. |
| "It passed — done" | If data was mutated directly, the restore hasn't run and been verified yet — and unexpected observations are findings, report them with evidence. |
