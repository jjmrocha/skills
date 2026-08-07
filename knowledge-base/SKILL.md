---
name: knowledge-base
description: Use when reading or writing a configured KB (wiki / plans / manuals) — system surfaces, helpers, patterns, plans, operator manuals — or ingesting docs, updating after code changes, or auditing for staleness. Requires kb_path in CLAUDE.md.
---

# Knowledge Base

A user-curated, agent-maintained KB. Three top-level buckets:

- **`wiki/`** — per-repo system docs (entities, interfaces, jobs, dependencies, events, rules, helpers, patterns). Answers *"what exists?"*
- **`plans/`** — implementation plans, often cross-repo. Answers *"what's intended?"*
- **`manuals/`** — operator-facing documentation in plain language, for readers without a technical background. Answers *"how do I use this?"*

## Core Principles (load-bearing)

1. **Code is truth; wiki is a finding aid.** Every wiki claim in your reply must be backed by code you read this turn. No "quick lookup" exemption.
2. **Writes autonomous; deletes require approval** (one exception — see [Delete protocol](references/operator-workflows.md#delete-protocol)). Wrong writes self-correct on the next read; deletes don't.
3. **Multi-file sources read in full.** No sampling.

## When NOT to Use

- No `kb_path` configured in CLAUDE.md → refuse; **do not invent a default**.
- Question is about code visible in the working directory → read the code directly.
- Personal memory (preferences, project state) → `~/.claude` memory, not the KB.

## Configuration

```yaml
kb_path: /Users/you/.kb/work    # required — absolute path. No default.
```

**Repo name resolution** (for writes): `git remote.origin.url` → `<repo>`, fallback to `git rev-parse --show-toplevel` basename, else ask once.

**Bootstrap requires approval.** If `<kb_path>` doesn't exist, ask before creating the canonical layout (`wiki/index.md`, `plans/index.md`, `manuals/index.md`, optional `git init`). The same applies to an existing KB missing one of the three buckets — ask before adding it. If `wiki/<repo>/` is missing, ask before creating it with the eight default subfolders: `entities/`, `interfaces/`, `jobs/`, `dependencies/`, `events/`, `rules/`, `helpers/`, `patterns/`. All eight are created at bootstrap (empty if no content) so downstream skills always find the expected layout.

## Folder Structure

```
<kb_path>/
  plans/       index.md + <ticket-or-branch>.md
  manuals/     index.md + <topic-slug>.md
  wiki/        index.md (lists repos)
    <repo>/    index.md (groups pages by subfolder)
      entities/ interfaces/ jobs/ dependencies/ events/ rules/ helpers/ patterns/
```

Three parallel entry points: `wiki/index.md`, `plans/index.md`, `manuals/index.md`. No KB-root index.

`manuals/` is flat, like `plans/` — a manual can cover the whole system, not just one repo. Filenames are topic slugs with no date prefix: plans are events, manuals are living documents.

## Operating Modes

The user's verb determines the mode.

| Mode | Trigger phrases | Discipline |
|------|-----------------|------------|
| **Query** | *"what's the orders schema"*, *"is there a plan for PROJ-1234"* | Read-only. **Read cited code.** |
| **Ingest** | *"read this doc and store what's relevant"*, *"ingest the schema from `<path>`"* | Write directly; **report coverage**; summarize. |
| **Update** | *"update the wiki with what we just changed"* | Write directly; summarize. Deletes → protocol. |
| **Lint** | *"audit the KB"*, *"check for stale pages"* | Flag-only **except** auto-delete of unprotected pages with all-dead in-tree sources. Plans and manuals are never auto-deleted. |

**Write modes load their protocols on demand.** Query is read-only and detailed inline below. The full Ingest, Update, Lint, and Delete protocols — including the advisory write lock, ingest coverage rules, the seven lint checks, and the delete-verdict table — live in [references/operator-workflows.md](references/operator-workflows.md). Load that file the moment the user's verb is a write; don't write from memory.

### Query workflow

1. Read `wiki/index.md`, `plans/index.md`, or `manuals/index.md`.
2. Read the relevant page(s) to find `sources:` paths.
3. **Open the cited code and read it.** This step is non-negotiable. The wiki is the index entry; the code is the answer.
4. Synthesize the answer **from the code**, using the wiki only for surrounding context (rationale, ownership, related surfaces).
5. **Cite both** in your reply: the code file you read this turn AND the wiki page that pointed you there.
6. If code disagrees with wiki — even minor — **surface the disagreement explicitly**, give the code's answer as truth, flag the page for update. Never silently prefer one side.
7. If neither has the answer, say so. Offer to add it once clarified.

**A manual is never the answer to a technical question.** Manuals are derived output, downstream of code and wiki. Read one only when the user asks about the manual itself; otherwise answer from code, as above.

## Page Format

YAML frontmatter (`summary`, `sources` ≥1 entry, `last_updated: YYYY-MM-DD`, `kind:` on `patterns/` and `manuals/`) + Markdown body. Wiki-links use **paths from the KB root, no extension**: `[[wiki/<repo>/entities/<name>]]`, `[[plans/<ticket>]]`. Citations live in `sources:`, never inline (use `[needs source]` for unsupported claims). Full template, per-subfolder body shape, and the special-case rule for `wiki/index.md` (uses standard markdown links): [references/page-template.md](references/page-template.md), [references/index-templates.md](references/index-templates.md).

`helpers/` and `patterns/` have a specific inclusion bar and creation channel — see [references/helpers-and-patterns.md](references/helpers-and-patterns.md).

## Manuals

A manual explains part of the system to a human operator with no technical background. Same sourcing discipline as the wiki — every claim traced in `sources:` — in a different register.

**`kind:` is required.** `explainer` (*"what the valuation pipeline does and why"*) or `how-to` (*"run a valuation"*). Body shape per kind: [references/page-template.md](references/page-template.md).

**Write channel:**
- **Creation is explicit.** Write a manual only when the user asks for one. Deciding a subject deserves an operator doc is a human call — never create one as a side effect of another task.
- **Refresh is automatic.** In Update mode, when a file you changed appears in an existing manual's `sources:`, rewrite the affected part in the same pass. Same as `wiki/`.
- **Deletion always requires approval.** Manuals are never auto-delete candidates, whatever their sources say.

**Register rules, applied when you write:**
- No fenced code blocks except commands the operator literally types.
- Every technical term defined on first use; no unexplained repo or module names.
- **No `[[wiki-links]]` in the body** — an operator can't follow them and they leak jargon. Wiki provenance goes in `sources:`. Manual → manual body links are fine.

Lint checks manuals for dead sources, aging, orphans, and `kind:` validity — not for readability. That part is yours at write time.

## Integration with Other Skills

When `kb_path` is configured, `brainstorm`, `analyze-code`, and `using-software-specialists` load this skill and read the repo's `wiki/<repo>/index.md` (including `Helpers` and `Patterns`) plus the matching `plans/<branch-or-ticket>.md` before producing code or findings. They are **read-only consumers**. Helper and pattern *creation* happens only through Ingest (explicit user request) or Update (after a code change you just made). Full integration matrix: [references/integrations.md](references/integrations.md).

## Wiki ↔ Code Disagreements

Any divergence — silent claim, reinvented helper, violated `patterns/` convention — is a **finding**, not a silent reconciliation. Answer from code, flag the page, suggest `/knowledge-base update`. Severity routing for `analyze-code` consumers: [references/integrations.md](references/integrations.md).

## Common Mistakes

| Mistake | Fix |
|---|---|
| Inventing a `kb_path` default | Refuse; ask user to set it in CLAUDE.md |
| Citing only the wiki in your reply | Cite both: code file read this turn + wiki page that pointed you there |
| Listing only the first contributing file under `sources:` | List **every** file that contributed |
| Inline `(source: ...)` in page body instead of `sources:` frontmatter | Provenance belongs in frontmatter so lint can audit it |
| Answering a technical question from a manual | Manuals are derived output. Answer from code |
| Writing a manual because a subject looked like it needed one | Creation is explicit. Wait to be asked |

YAML quoting, "quick lookup" temptation, multi-file ingest coverage, delete-protocol bypasses, approval theater, and other edge cases: [references/common-pitfalls.md](references/common-pitfalls.md).
