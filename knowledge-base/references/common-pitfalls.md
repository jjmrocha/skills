# Common Pitfalls — Extended Notes

The headline mistakes are in SKILL.md's *Common Mistakes* table. This file expands on the ones that warrant more than one line.

## YAML quoting

The single biggest source of broken pages. **Wrap any non-trivial string in double quotes.**

Unquoted, YAML treats reserved indicators as syntax — frontmatter breaks. Worse, unquoted bareword values that look like booleans or numbers get **silently coerced** (`summary: no` → boolean `false`; `summary: 1.0` → float `1.0`), which lint won't catch because the YAML is "valid," just wrong.

**Quote any value containing anything beyond letters, digits, spaces, hyphens, underscores, or dots.** Specifically: `:` followed by space, `::`, leading `#`, `&`, `*`, `!`, `|`, `>`, `{` `}` `[` `]`, `,`, `?`, `%`, `@`, or `` ` ``.

```yaml
summary: "Path: foo"
summary: "parse_iso (in helpers/dates.md)"
summary: "yes — the cancellable window"
```

**Default: quote.** Filenames are different — they're not YAML, but they ride the same risk surface in shells and tools; stick to lowercase letters, digits, and hyphens. Avoid programming-language shorthands like `path::symbol` (Rust/C++) — say it in English: *"`parse_iso` in `helpers/dates.md`"*.

## "Quick lookup" temptation

There is no quick-lookup exemption. The same drift that produces consequential bugs produces casual misinformation, and the question alone rarely reveals which one the user is about to act on. Open the cited code every time — even for a one-line answer.

## Coverage on multi-file ingest

Multi-file sources must be enumerated and read **in full**. List every file first, then read each. Skipping = missing surfaces. The Ingest summary's coverage line (`Ingested M/M files`) is mandatory; partial coverage must be reported as such, not hidden. A `Wrote N pages` summary without `Ingested M/M files` is incomplete and forbidden.

## "User said delete"

A user instruction to delete a page **does not** authorize bypassing the Delete protocol. Only the `safe-to-delete` verdict from `check-sources.py` is autonomous. Every other delete reason — merges, restructures, "obsolete," "we don't need this anymore" — requires explicit approval after you show what will be deleted and which inbound `[[wiki-links]]` will break.

## Cross-repo `[[wiki-links]]` during `analyze-code`

The cross-repo lookup is **soft**. Follow only when judged relevant to the audit. Don't recursively chase every cross-repo link.

## Source-path renames during lint

Lint flags path issues; the user fixes them. Auto-*delete* of all-dead-source pages is allowed; auto-*fix* of paths is **not**. A rename means "update the path," not "delete the page" — and the agent shouldn't update silently either, because the rename could itself be a mistake or part of an in-flight refactor.

## Approval theater

Asking for diff approval before every write rubber-stamps at scale and is worse than no approval. Write directly; summarize after. The wiki self-corrects when readers follow its pointers; deletes are the only operation that needs the brake.

## Auto-deleting partial-source pages

Delete only when **all** in-tree sources are dead. If even one source is alive, drop the dead entries from `sources:` and flag the page for review — don't delete.

## Plan page deletion

Plans are never auto-deleted, even when their sources are dead. A plan describes intent; intent can outlive the code that originally implemented it (e.g., the implementation was rolled back; the plan still records what was tried and why). Flag only; the user decides.

## Cross-repo source verification

If a page's `sources:` reference a repo other than the one the agent is currently in, the agent can't verify code in repos it isn't in. Flag, never auto-delete.

## Personal memory in the wiki

User preferences, session state, deadlines, in-flight project state → Claude Code's `~/.claude` auto-memory, not the wiki. The wiki is for *system* knowledge.

## Helpers inclusion bar (recap)

The helpers/ bar is *reusable across the repo, non-private*. Feature-internal helpers stay with their feature. Private functions (Python `_`-prefixed, etc.) never appear. See [helpers-and-patterns.md](helpers-and-patterns.md).

## Pattern page creation by specialists

Pattern *pages* are Ingest-only. The user decides what's canonical. Updating an existing pattern page when its exemplar drifts is fine — that's a normal Update.

## Pattern `kind:` requirement

`kind:` is required on every page under `patterns/` (lint check 7). Choose `convention | recipe | template`, or don't write the page.
