# Content Page Template

Use this template for every page under `<kb_path>/wiki/<repo>/entities/`, `interfaces/`, `jobs/`, `dependencies/`, `events/`, `rules/`, `helpers/`, `patterns/`, or under `<kb_path>/plans/` or `<kb_path>/manuals/`. The skill's `index-templates.md` covers the special index pages instead.

---

```markdown
---
summary: One or two sentences describing what this page covers.
sources:
  - <path | url | session note>      # see "Source value formats" below
last_updated: YYYY-MM-DD
---

# <Page Title>

<Body content. Short paragraphs, clear headings.>

Link related concepts inline using `[[wiki-links]]` (paths from the KB root):
- `[[wiki/order-service/entities/orders]]` — page inside a repo.
- `[[plans/proj-1234]]` — a plan.
- `[[wiki/order-service]]` — repo's index.md (shorthand: a link to a repo with no further path resolves to its `index.md`).

If a claim can't be sourced, mark it `[needs source]` inline.

## Related pages
- [[wiki/<repo>/<subfolder>/<page>]]
- [[wiki/<repo>/<subfolder>/<page>]]
```

---

## Self-check before writing

Run through this **before** saving any page:

- [ ] Every factual claim has a corresponding entry in `sources:` OR an inline `[needs source]` marker.
- [ ] `[[wiki-links]]` resolve to files that exist (or will exist by the end of this write).
- [ ] `last_updated` is today's date.
- [ ] The page is also linked from its index — `wiki/<repo>/index.md` for wiki pages, `plans/index.md` for plans, `manuals/index.md` for manuals (update both in the same write).

---

## Required frontmatter fields

| Field | Type | Notes |
|-------|------|-------|
| `summary` | string | One or two sentences. Surfaced in the repo's `index.md`. |
| `sources` | list of strings | At least one entry. See formats below. |
| `last_updated` | date | `YYYY-MM-DD`. Lint flags pages older than 90 days as "needs review". |
| `kind` | string | **Required on pages under `patterns/` and `manuals/`.** `patterns/`: one of `convention`, `recipe`, `template`. `manuals/`: one of `how-to`, `explainer`. Lint check 7 enforces presence and enum. |
| `repos` | list of strings | **`plans/` and `manuals/` only.** Which repos the page covers. Omit on a whole-system manual. |

## Source value formats

| Source type | Example value |
|---|---|
| Live code file | `src/orders/models.py` (relative to the repo root) |
| External doc | `https://confluence.company.com/x/abc123` |
| Session learning | `session 2026-05-22 — user described order cancellation flow` |
| Another wiki page | `[[wiki/order-service/events/order-created]]` |

## Subfolder-specific body shape

Each subfolder has a conventional shape. The body content adapts; the frontmatter stays the same.

| Subfolder | What to document in the body |
|---|---|
| `entities/` | Table name, columns + types, primary key, foreign keys, constraints, indexes. List enum values if any. |
| `interfaces/` | Method, full path, request shape, response shape, error codes, auth requirement. **Do not list calling services** — callers link to this page one-way from their own `dependencies/` pages (see [Cross-repo linking](operator-workflows.md#cross-repo-linking)). |
| `jobs/` | Schedule (cron expression), trigger condition, what it does, dependencies (DB/services it touches), failure behavior. |
| `dependencies/` | URL/endpoint, auth method (API key, OAuth, mTLS), rate limits, owner team, what this repo uses it for. **If the called service is a repo on the wiki, link its `interfaces/` page one-way** — `[[wiki/<other-repo>/interfaces/<page>]]` (see [Cross-repo linking](operator-workflows.md#cross-repo-linking)). |
| `events/` | Topic name, schema (payload fields + types), ordering/delivery guarantees, and whether this repo **produces** or **consumes** the topic. A **consumed** event links one-way to the producer's page when the producer is a repo on the wiki — `[[wiki/<other-repo>/events/<page>]]`. Links flow **consumer → producer only**; producer pages don't track consumers (see [Cross-repo linking](operator-workflows.md#cross-repo-linking)). |
| `rules/` | The business rule in plain language, the entities/endpoints where it's enforced (linked), examples of valid and invalid states. |
| `helpers/` | One file per category (e.g., `dates.md`). Body: a `## Helpers` table with columns `Helper`, `Signature`, `Use when` — one row per qualifying function. Optional `## Notes` for cross-cutting context (returns are timezone-aware, inputs are immutable, etc.). `sources:` lists the file(s) where the listed helpers live. Signature column is a hint; the agent always reads the actual code before using. |
| `patterns/` | One file per pattern; `kind:` frontmatter required. Body: `## When to use` (1–3 sentences, symptoms/triggers), `## The pattern` (the rule for `convention`, numbered steps for `recipe`, a ≤30-line snippet for `template`), `## Exemplar` (pointer to the file(s) in `sources:`), `## Related` (linked helpers/patterns/rules). `sources:` cites canonical exemplar file(s). |
| `plans/` | Goal, repos touched (frontmatter `repos: [...]`), entities/interfaces/events affected (linked), status (Draft / Active / Done / Abandoned). |
| `manuals/` — `kind: explainer` | `## In short` (what this is, two or three sentences), `## How it works` (plain language, no code), `## Terms` (each piece of jargon the body uses, defined). |
| `manuals/` — `kind: how-to` | `## Before you start` (prerequisites), `## Steps` (numbered, one action each), `## If something goes wrong` (symptom → what to do). |

**Manuals are written for a human operator with no technical background.** No fenced code blocks except commands the operator literally types; no `[[wiki-links]]` in the body (provenance goes in `sources:`); every technical term defined on first use. Manual → manual body links are fine.
