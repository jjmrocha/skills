# guided-test

A Claude Code skill for manually verifying a change against a real environment
with real data. The agent guides one step at a time: it proposes a single
action, waits for the output, interprets it, and only then proposes the next.

## When to Use

* Verifying a fix or feature behaves correctly on a local or staging environment
* Confirming a change works against real data before merging or releasing
* Testing a code path that only manifests with production-shaped data

## When Not to Use

* Writing automated tests → `test-driven-development` / `writing-unit-tests`
* Auditing the code itself → `analyze-code`
* Answering questions about how code works → `research`
* Production environments — not supported

## What It Enforces

* **One step per message.** No multi-step plans, no branching instructions.
* **Matched pair.** Both the case that must change and the case that must not
  have to be observed before anything is called a pass.
* **Real creation paths first.** Run the job or use the UI; direct database
  mutation is a fallback that must be justified.
* **Restore point first.** The restoring statement is captured before the first
  mutation, and blast radius is stated before any trigger.

## Output

A verification report delivered in the conversation: what was under test, the
environment, the subject chosen and why, each case with its predicted and
observed evidence, any unexpected observations as separate findings, and
confirmation that cleanup restored the recorded state.
