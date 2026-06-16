# knowledge-base — operator workflows

**Load this file when the user's verb is a write:** Ingest, Update, Lint, or autonomous Delete. The Query (read-only) path in `SKILL.md` does **not** need this file — consumers (`brainstorm`, `using-software-specialists`, `analyze-code`) never load it.

## Write lock (Ingest, Update, autonomous Delete)

Multi-file writes aren't atomic. Take the advisory lock before writing; release after summary:

```bash
uv run scripts/kb-lock.py acquire <kb_path>   # exit 1 if blocked
# ... writes ...
uv run scripts/kb-lock.py release <kb_path>
```

If `acquire` exits non-zero, **stop**, surface the holder's PID and acquired-at to the user, don't write. Stale locks (>1h) reclaim automatically.

## Ingest workflow

Acquire the write lock; release on summary success.

1. **Enumerate the full source set, then read every file.** If the source resolves to more than one file, list every file first (`git ls-files`, `find <dir> -type f`, archive listing). Then read each. **No sampling.** The only allowed exclusions are files the user explicitly named out-of-scope, or boilerplate with no system surface (lockfiles, generated code, vendored deps, binary assets) — announce any exclusion in the summary.
2. Identify the destination: which repo, which subfolder under `wiki/<repo>/`, or `plans/`. Ask only when the source is genuinely ambiguous; for clean sources, pick the best fit and surface the choice in the summary.
3. For each page: create or update; add `[[wiki-links]]`; set `sources:` (listing **every** contributing file) and `last_updated:`.
4. **Cross-repo linking.** Forward-link the consumer pages you wrote, and backfill other repos' consumer pages that the surfaces you just documented now satisfy — see [Cross-repo linking](#cross-repo-linking).
5. Update the affected `wiki/<repo>/index.md` and the top-level `wiki/index.md` if a new repo or top-level page was added.
6. **Summary is mandatory and leads with a coverage line:**
   ```
   Ingested 17/17 files from docs/architecture/ (0 excluded).
   Wrote:
     + wiki/order-svc/dependencies/sendgrid.md   email provider
     + wiki/order-svc/events/order-created.md    schema, producers, consumers
     ~ wiki/order-svc/index.md                   linked new pages
   ```
   Excluded files get a line each with the reason. **Coverage rule:** if read-count ≠ in-scope-count, you ingested partially — go back to step 1. Reporting "Wrote N pages" without "Ingested M/M files" is incomplete and forbidden.

## Update workflow

Acquire the write lock; release on summary success.

1. Identify pages affected by the change.
2. Write directly. Add `[[wiki-links]]`; set `last_updated:`.
3. **Cross-repo linking** per [Cross-repo linking](#cross-repo-linking).
4. Update the repo's `wiki/<repo>/index.md` and `wiki/index.md` as needed.
5. Summarize: one line per page, scannable (`+ new`, `~ updated`).
6. Deletes → [Delete protocol](#delete-protocol).

## Cross-repo linking

A dependency or consumed event often points at another service that is *also*
documented in this KB. The link lives on the **consumer/caller** side, one-way
(consumer → producer); never back-edit the upstream page to record its callers.
Do **both** of the following on every Ingest and Update:

1. **Forward-link as you write.** When writing a `dependencies/` or a consumed
   `events/` page, take the referenced surface — the HTTP method+path
   (`GET /stock/{sku}`) or the topic/event name (`stock-updated`) — and search
   the wiki for a repo that owns it (`interfaces/` for endpoints, `events/` for
   topics). If one does, add the one-way link
   `[[wiki/<other-repo>/interfaces/<page>]]` or
   `[[wiki/<other-repo>/events/<page>]]`. If none owns it yet, write the page
   without the link and mark the surface `[needs source]`; backfill catches it
   when the owner is ingested.

2. **Backfill when you ingest a repo's interfaces/events.** After writing this
   repo's producer-side `interfaces/` and `events/` pages, scan **every other
   repo's** `dependencies/` and consumed `events/` pages for references to the
   surfaces you just documented (match on method+path or topic name; the
   `[needs source]` / "external" markers left by an earlier ingest are the
   strongest signal). For each match, add the one-way `[[wiki-link]]` on that
   consumer page and clear the stale "external / not documented" marker.
   **This is in scope** — you are adding the consumer-side outbound link, not
   rewriting another repo's content. Skipping it because "that's a different
   repo" is the exact failure this step exists to prevent.

**Producer pages never name their consumers.** When you create or update an
`interfaces/` or producer-side `events/` page, do not list or link the services
that call or consume it — even if a consumer is already on the wiki. The link is
recorded only on the consumer's page. A producer that enumerates consumers
recreates the bidirectional maintenance burden (every new consumer edits the
producer's repo) that one-way linking exists to avoid.

Report every cross-repo link you created or backfilled in the summary.

## Lint workflow

```bash
uv run scripts/lint.py <kb_path> --json
```

**Don't load pages into context to run lint manually** — the script keeps bodies out. Read the structured report. The seven checks:

1. **Broken `sources:` paths** — script flags renames vs dead files separately; doesn't auto-fix paths.
2. **Aging pages** — `last_updated` >90 days. Flag as *"needs review"*, not *"stale"*.
3. **Orphan pages** — no inbound `[[wiki-link]]`.
4. **Concept-gap candidates** — regex heuristic; triage by reading.
5. **`[needs source]` markers** — unsourced claims.
6. **All-dead in-tree sources** — non-plan pages with every `sources:` path truly dead (no rename) are **auto-delete candidates** per the [Delete protocol](#delete-protocol). Plans are flagged, never deleted. Renamed → not eligible (update path instead).
7. **Pattern `kind:` validity** — pages under `patterns/` must declare `kind:` set to `convention | recipe | template`.

Surface 1, 2, 3, 5, 7 to the user; triage 4 by reading; for 6 candidates, verify each with `check-sources.py` before deleting.

## Delete protocol

```bash
uv run scripts/check-sources.py <page-path>
```

| Verdict | Action |
|---|---|
| `safe-to-delete` | All in-tree sources dead, no externals, not a plan, current repo matches page repo. **Delete autonomously.** |
| `partial` | Drop dead/renamed entries from `sources:`; flag for review. Don't delete. |
| `flag (renames)` | Update source paths. Don't delete. |
| `flag (external / cross-repo / plan / no-sources)` | Surface to user. Don't delete. |
| `all-alive` | Nothing to do. |

**Autonomous delete = only `safe-to-delete`. Every other delete reason (page obsolete for non-source reasons, merging, restructuring, "user said delete") requires explicit approval.** Before approved deletes, show what's about to be deleted and which inbound `[[wiki-links]]` will break.

Autonomous deletes still take the [write lock](#write-lock-ingest-update-autonomous-delete) around the delete + index updates.

After any delete: remove the entry from the repo's `index.md` and `wiki/index.md`. Include the delete in the post-action summary.
