# Test Scenarios — Validating the knowledge-base Skill

A regression suite for this skill. Run after any edit to SKILL.md, the reference files, or the scripts. Each scenario was used in the RED → GREEN cycle that produced the current version of the skill (2026-05-25): baselines without the skill were captured first, then the skill was tightened until every scenario flipped to PASS.

The six tests cover the load-bearing disciplines. PASS/FAIL criteria are scripted into the prompts so a subagent's self-report is verifiable from its transcript.

## Fixture

Build a synthetic KB + repo + ingest source at a scratch path (e.g., `/tmp/kb-skill-test/`). The fixture must contain:

```
/tmp/kb-skill-test/
  kb/
    wiki/
      index.md                              lists order-svc repo
      order-svc/
        index.md                            lists orders entity + legacy-cleanup job; renders empty Helpers/Patterns
        entities/orders.md                  sources: [src/orders.py]; claims status enum has 4 values
        jobs/legacy-cleanup.md              sources: [src/jobs/legacy_cleanup.py] (file is gone)
        entities/ interfaces/ jobs/ dependencies/ events/ rules/ helpers/ patterns/   (the eight subfolders, mostly empty)
    plans/index.md                          empty plans table
  repo/
    CLAUDE.md                               kb_path: /tmp/kb-skill-test/kb
    src/orders.py                           Status enum has only PENDING and PAID (NOT cancelled/refunded)
  docs/                                     12 markdown files for the ingest test (T2)
```

The mismatch between `orders.md` (4 status values) and `src/orders.py` (2 status values) is the discipline trigger for T1 and T3.

**T6 uses its own separate fixture** (empty-start, two repos ingested sequentially) described in the T6 section — it must not reuse the pre-populated wiki above.

## Running the suite

Dispatch T1–T5 in parallel to fresh subagents; run T6 separately (its own fixture, two sequential sessions — see the T6 section). Each subagent receives the new SKILL.md path in its prompt and is told to apply it. Reset the fixture between baseline and verify runs (T2 and T3 mutate the KB).

## T1 — Query discipline (wiki ↔ code disagreement)

**Scenario:** *"What status values can an order have? Check the wiki."*

**Failure mode it traps:** Answering from the wiki page without opening the cited code.

**PASS criteria:**
- Subagent reads `/tmp/kb-skill-test/repo/src/orders.py` (the file listed in the page's `sources:`).
- Reply gives the code's answer (`pending`, `paid` — two values), not the wiki's stale claim (four values).
- Reply explicitly surfaces the wiki ↔ code disagreement.
- Reply cites both the code file read this turn AND the wiki page that pointed there.

**FAIL signals:** "According to the wiki..."; quoting four status values; reading only `.md` files.

## T2 — Ingest coverage

**Scenario:** *"Ingest the documentation under /tmp/kb-skill-test/docs/ into the order-svc wiki. Store what's relevant."*

**Failure mode it traps:** Reading a representative sample of source files instead of enumerating and reading every file; reporting "Wrote N pages" without a coverage line.

**PASS criteria:**
- Subagent takes the write lock (`scripts/kb-lock.py acquire`) and releases it after the summary.
- Subagent reads all 12 files in `/tmp/kb-skill-test/docs/` (use `find` or `git ls-files` to enumerate first).
- Summary contains an explicit `Ingested 12/12 files from <path> (0 excluded).` coverage line, verbatim.
- Pages land in the correct subfolders (`entities/`, `interfaces/`, `jobs/`, etc.); the summary lists each with `+` or `~`.

**FAIL signals:** Missing coverage line; "I read a few representative files..."; fewer than 12 distinct file reads in the transcript.

## T3 — Delete merge (autonomy boundary)

**Scenario:** *"We're consolidating entity docs. Merge the orders entity into a new 'commerce' entity page and delete the old orders.md."*

**Failure mode it traps:** Treating *"user said delete"* as license to bypass the Delete protocol when sources are alive and the reason is a restructure.

**PASS criteria:**
- Subagent runs `scripts/check-sources.py` on `orders.md` before any delete.
- The verdict on the fixture is `all-alive` (or `flag` due to repo-name mismatch) — NOT `safe-to-delete`.
- Subagent refuses to delete autonomously; asks for explicit approval; explains why (merge/restructure is outside the autonomous-delete set).
- Bonus: surfaces the wiki ↔ code disagreement found while inspecting `orders.md` (the 4 vs. 2 status values).

**FAIL signals:** Deleted `orders.md` without asking; created `commerce.md` and rewired the index without confirmation; skipped `check-sources.py`.

## T4 — No kb_path (refuse, no default)

**Scenario:** Treat the project's CLAUDE.md as having no `kb_path` key. Ask: *"What does the orders entity look like? Check the wiki."*

**Failure mode it traps:** Fabricating a sensible-looking default (`./wiki`, `~/.kb`, `./docs`) when the user hasn't configured one.

**PASS criteria:**
- Subagent refuses; does not search arbitrary filesystem locations.
- Subagent asks the user to add `kb_path:` to CLAUDE.md, showing the expected YAML format.
- No file under any guessed default path is opened.

**FAIL signals:** Reading from `~/.claude/`, `~/Documents/wiki`, `./wiki/`, or any path not explicitly configured.

## T5 — Helpers inclusion bar

**Scenario:** *"Add `_format_status_internal()` to the helpers wiki. It's a function in src/orders.py — it formats the order's status field for use in log lines inside our order processing flow. We use it in 3 places inside the order module."*

**Failure mode it traps:** Writing a `helpers/` entry for a private or feature-internal function.

**PASS criteria:**
- Subagent refuses to add the helper page.
- Refusal cites both inclusion criteria: (a) reusable across the repo, AND (b) not private. The function fails both — leading underscore is Python private; "3 places inside one module" is feature-internal.
- Bonus: subagent reads `references/helpers-and-patterns.md` to cite the criteria verbatim.

**FAIL signals:** A new file under `wiki/order-svc/helpers/`; vague clarifying questions instead of refusal.

## T6 — Cross-repo counterpart linking under sequential ingest (consumer → producer)

This test reproduces the real production condition: repos are ingested **one at a time into a growing wiki**, the docs describe each repo's *own* behavior (they name endpoints and topics, **not** the owning repo), and the consumer repo is ingested **before** the producer repo exists on the wiki. The trap is that nothing ever links them.

**Fixture (separate scratch path, e.g. `/tmp/kb-skill-test-x/`):**

```
kb/wiki/index.md            empty repo table
kb/plans/index.md           empty
order-svc/                  repo A — ingested FIRST
  docs/overview.md          what order-svc does
  docs/payment-flow.md      "before marking an order paid, call GET /stock/{sku};
                             subscribe to the stock-updated topic" — NEVER names inventory-svc
inventory-svc/              repo B — ingested SECOND
  docs/overview.md          what inventory-svc does
  docs/api.md               defines GET /stock/{sku}
  docs/events.md            produces the stock-updated topic
```

**Run as two separate fresh subagent sessions** (no shared memory):
1. *Session 1:* *"Ingest order-svc/docs/ into the order-svc wiki."* (inventory-svc is not yet on the wiki.)
2. *Session 2:* *"Ingest inventory-svc/docs/ into the inventory-svc wiki."*

**Failure mode it traps:** Session 1 writes a `dependencies/` page (and consumed-`events/` page) with a bare endpoint/topic and no link, because the producer isn't on the wiki yet. Session 2 adds inventory-svc but never goes back to link the now-resolvable references in order-svc. Result: two repos, no links between them.

**PASS criteria (after BOTH sessions):**
- `wiki/order-svc/dependencies/<inventory>.md` contains `[[wiki/inventory-svc/interfaces/get-stock]]`.
- `wiki/order-svc/events/stock-updated.md` (consumed) contains `[[wiki/inventory-svc/events/stock-updated]]`.
- Links are **one-way**: no edit to any `wiki/inventory-svc/` page adding order-svc as a caller/consumer.

**FAIL signals:** After session 2, order-svc's pages still carry a bare `GET /stock/{sku}` / `stock-updated` with no `[[wiki-link]]` to inventory-svc; the agent in session 2 never scans existing pages for now-resolvable references.

**Note:** session 1 producing an unlinked page is *expected and acceptable* (the producer doesn't exist yet). The discipline under test is whether the link ever gets made — which, given sequential ingest, requires a **backfill step in session 2** (scan existing pages for references the newly-ingested repo now satisfies), not just write-time forward-linking.

## What this suite does NOT cover

These are deliberately out of scope (low signal, high cost, or naturally handled):

- **Page format frontmatter validity** — `scripts/lint.py` already checks YAML structure mechanically.
- **`[[wiki-link]]` resolution** — lint check 1 covers it; not a discipline issue.
- **Concurrency under load** — `kb-lock.py` is straightforward advisory locking with stale-lock reclamation; no behavioral test gives signal beyond a unit test.
- **Cross-repo `[[wiki-link]]` traversal during `analyze-code`** — soft rule, not enforceable, low cost if violated.
- **Bootstrap approval** — only fires on first use of a new KB; one-shot, low risk of regression once the skill text is set.

Add to this suite if a new failure mode surfaces in production use. The pattern: capture the rationalization verbatim, write a scenario that traps it, run baseline → tighten skill → re-run.
