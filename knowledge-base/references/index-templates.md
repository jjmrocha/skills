# Index Templates

Templates for the four special files that aren't content pages: `wiki/index.md`, each repo's `wiki/<repo>/index.md`, `plans/index.md`, and `manuals/index.md`. Use [page-template.md](page-template.md) for everything else.

There is no KB-root `index.md` — `wiki/index.md`, `plans/index.md`, and `manuals/index.md` are parallel entry points.

---

## `wiki/index.md`

Lists every repo under `wiki/`. Updated when a new repo folder is created. Active plans are NOT listed here — they live in `plans/index.md`.

```markdown
# Wiki

## Repos
- [order-service](order-service/index.md) — Order placement, cancellation, fulfillment lifecycle.
- [user-service](user-service/index.md) — User accounts, authentication, profiles.
- [email-service](email-service/index.md) — Outbound email via SendGrid.
```

**Repo links use standard markdown with an explicit `index.md` target**, not the `[[wiki/<repo>]]` shorthand. Reason: `wiki/index.md` is the wiki's entry point — readers (and the user) browse it in plain markdown viewers, where `[[wiki-link]]` text is not clickable. The explicit `[<repo>](<repo>/index.md)` form is clickable everywhere and still resolves to the same target the shorthand would. Body text inside other pages can continue to use `[[wiki-links]]` for cross-references (that content is agent-consumed, not browsed).

---

## Per-repo `wiki/<repo>/index.md`

Lists every page in the repo, grouped by subfolder. Updated whenever a page is created, renamed, or removed in this repo.

```markdown
# <repo-name>

<One-paragraph description of what this repo is responsible for.>

## Entities
- [[wiki/<repo>/entities/<name>]] — <one-line summary from the page's frontmatter>

## Interfaces
- [[wiki/<repo>/interfaces/<name>]] — <method + path>

## Jobs
- [[wiki/<repo>/jobs/<name>]] — <schedule + purpose>

## Dependencies
- [[wiki/<repo>/dependencies/<name>]] — <external service name + purpose>

## Events
- [[wiki/<repo>/events/<name>]] — producer | consumer | producer+consumer

## Business rules
- [[wiki/<repo>/rules/<name>]] — <one-line summary>

## Helpers
- [[wiki/<repo>/helpers/<category>]] — <one-line summary of what's in this category>

## Patterns
- [[wiki/<repo>/patterns/<name>]] *(convention | recipe | template)* — <one-line summary>
```

Omit the six system sections (`Entities`, `Interfaces`, `Jobs`, `Dependencies`, `Events`, `Business rules`) when their subfolder is empty — drop the heading entirely.

**`## Helpers` and `## Patterns` are exceptions: always render the heading, even when empty.** When the corresponding subfolder has no pages yet, render it as `*(none yet)*` under the heading. This is load-bearing: `brainstorm`, `analyze-code`, and the specialists in `using-software-specialists` consult these two sections by name before producing code, and an absent heading is indistinguishable from "I forgot to look." Examples:

```markdown
## Helpers
*(none yet)*

## Patterns
*(none yet)*
```

In the `## Patterns` list, render the `*(kind)*` marker using the page's `kind:` frontmatter value, so the agent can scan by intent without opening each page.

---

## `plans/index.md`

Status table for every plan, regardless of repo. Sort by status (Active first), then by date descending.

```markdown
# Plans

| Plan | Date | Status | Repos | Goal |
|------|------|--------|-------|------|
| [[plans/proj-1234]] | 2026-05-22 | Active | order-service, email-service | Order cancellation flow. |
| [[plans/feature-search]] | 2026-05-10 | Active | search-service | Full-text product search. |
| [[plans/feature-jwt-auth]] | 2026-04-12 | Done | user-service | Migrate to JWT auth. |
| [[plans/feature-newsletter]] | 2026-02-03 | Abandoned | email-service | Newsletter system (deferred Q3). |
```

**Status values:** `Draft` | `Active` | `Done` | `Abandoned`.

---

## `manuals/index.md`

Every manual, sorted by kind then title. Updated whenever a manual is created, renamed, or removed — a manual missing from this table is reported by lint check 3 as an orphan.

```markdown
# Manuals

Operator-facing documentation in plain language. Derived from the code and the wiki; the code remains canonical.

| Manual | Kind | Repos | Last updated |
|---|---|---|---|
| [[manuals/running-a-valuation]] | how-to | mocho | 2026-08-07 |
| [[manuals/how-valuation-works]] | explainer | mocho | 2026-08-07 |
| [[manuals/reading-the-daily-report]] | explainer | *(whole system)* | 2026-08-07 |
```

**Kind values:** `how-to` | `explainer`. Leave `Repos` as `*(whole system)*` when the manual's frontmatter omits `repos:`.
