---
name: guided-test
description: Use when the user wants to verify a feature or fix behaves correctly on a real environment (local or staging) with real data — manual verification guided step by step, one action at a time. Triggers on "help me test this on staging", "guide me through testing X", "verify this works on the team env", "how do I test this manually".
---

# Guided Test — Manual Verification on a Real Environment

Prove a change behaves correctly against real data on a real environment. The user is the hands: the agent proposes exactly one action, the user runs it and pastes the output, the agent interprets it and proposes the next. Nothing is asserted that was not observed.

**If the conversation was compacted, re-invoke this skill before continuing.**

## When NOT to Use

| Situation | Instead |
|---|---|
| Writing automated tests | `test-driven-development` / `writing-unit-tests` |
| Auditing the code itself | `analyze-code` |
| Answering "how does X work" from the code | `research` |
| Production environment | Not supported — local or staging only |

## Hard Rules

1. **One step per message.** A single action, then wait. Never a numbered list of five steps, never a branch tree of "if X then... else...". The next step is not knowable until the current output is read.
2. **Matched pair required.** A verification passes only when *both* the case that must change and the case that must not have been observed. A single negative result proves nothing — a query matching nothing produces the identical output. Before reading any negative result, **confirm the trigger actually ran**; a no-op run yields a perfect-looking false negative.
3. **Prefer real creation paths.** Produce data by running the job, using the UI, or calling the endpoint. Direct database mutation is a fallback and must be justified out loud — name the real path and why it is unavailable.
4. **Restore point first.** Capture and echo back the exact restoring statement before the first mutation. State the blast radius of any trigger before running it.

## Workflow

Each phase's output is stated back to the user before the next begins.

### Phase 1 — Establish intent

What is supposed to change, in one paragraph, naming the specific condition that changed. Sources in priority order:

1. The implementation plan in the KB plans dir — if `kb_path` is configured and one exists (load `knowledge-base`).
2. The ticket — if the branch name or the user names one (`jira-reader`).
3. The diff — `git diff <base>...HEAD`, scoped to the change under test.

Read all that are available; the diff is authoritative when they disagree. Tickets are often empty or stale — say so rather than inferring acceptance criteria that were never written. If none of the three yields intent, ask.

**Output:** the changed condition, stated precisely enough to predict outcomes from. "Batches are now only linked when they have a non-deleted claim whose transaction is already in the statement" is usable. "The query was fixed" is not.

### Phase 2 — Map the path and the triggers

Trace the changed symbol to its callers, then out to entry points: CLI job, HTTP route, subscriber, scheduled job, UI action. Then read the **environment's own deployment config** — Helm values, env manifests, compose files — to learn which of those exist on the target environment, on what schedule, and under which feature flags.

**Output:** the trigger options with trade-offs, and a recommendation. Prefer the narrowest trigger that reaches the changed code. A client-scoped or record-scoped entry point beats a global batch job; a global job that already runs nightly beats a flow that rejects and rebuilds unrelated state.

Note environment flags that gate the code path — a feature disabled by config on the target environment makes the test impossible before any data is examined.

### Phase 3 — Feasibility ladder

One rung per message, each a single query. Climb only as far as needed:

1. **Does data of the required shape exist?** Counts and date ranges, not row dumps.
2. **Is the configuration that enables the feature turned on?** Read the gate conditions from the code, then check them in the data — quote the code that requires each flag.
3. **Can the case actually be constructed?** Check the selection predicates of whatever would create the data. They are usually stricter than expected.

**"This environment cannot test this — here is what is missing" is a valid outcome.** Say it plainly rather than forcing a weak test. Report which rung failed and what would have to change.

### Phase 4 — Design the matched pair, and predict

Name both cases and why each qualifies:

- **Subject** — must *not* change. It satisfies every condition the old code required, and fails exactly the one the change added.
- **Control** — must change. It satisfies the new condition too, proving the mechanism still works.

Then **write the predicted outcome of both before anything runs**. Prediction first is what stops a surprising result from being rationalized after the fact. If the subject and control cannot be isolated to a single differing condition, the test is not yet designed — keep working on it.

### Phase 5 — Execute

Record the restore point, then setup → trigger → observe, one action per message.

Message format:

```
**Step N.** <why this step exists — one sentence>

<one command or one query block>

<what to paste back>
```

- Interpret the output before proposing the next step. State what it means.
- If the output contradicts the prediction, **stop and re-derive** from the code. Do not improvise forward.
- **Every mutation step ends with a verification read in the same message.** Users frequently execute only the statement under the cursor; a trailing `SELECT` catches it immediately.
- Prefer a mutation and its verification in one step over splitting them; prefer splitting two independent mutations over combining them.

### Phase 6 — Report and restore

Deliver the report in the conversation — do not write it to a file unless asked. Then restore the recorded state and verify the restore landed.

Unexpected observations are the most valuable output. A verification that passes and also reveals a consequence nobody planned for has earned more than a green check. Report those as separate findings with their own evidence.

## Report Template

```markdown
# Verification: <feature / ticket>

**Environment:** <local | staging env name>
**Intent source:** <KB plan path | ticket KEY | diff range>
**Under test:** <the condition that changed, one paragraph>

## Subject chosen
<what was used and why it qualifies — including what was ruled out and why>

## Cases

| Case | Setup | Predicted | Observed | Verdict |
|---|---|---|---|---|
| <name> | <what was arranged> | <written before the run> | <evidence> | pass/fail |

## Findings
- <unexpected observation> — <evidence> — <impact> — <suggested fix, with file:line>

## Cleanup
<statements run to restore, and the verified end state>
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

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Issuing a multi-step plan up front | One step, then wait. The next step depends on the output |
| Branching instructions ("if X do this, else that") | Ask for the output and branch yourself |
| Accepting a single observed case as proof | Matched pair — subject *and* control, both observed |
| Reading a negative result without confirming the trigger ran | A no-op run looks identical to a correct negative |
| Predicting after the fact | Write both predictions before executing |
| Hand-writing SQL to create data | Use the job, the UI, the endpoint. Justify any fallback out loud |
| Mutating before recording a restore point | Capture and echo the restoring statement first |
| Triggering a client-wide or global job silently | State blast radius before running it |
| A mutation step with no verification read | Trailing `SELECT` in the same message — partial execution is common |
| Forcing a test the environment cannot support | "Rung 2 failed, here's what's missing" is a valid, honest outcome |
| Reporting only pass/fail | Unexpected observations are findings — report them with evidence |
| Leaving mutated state behind | Restore, then verify the restore |
