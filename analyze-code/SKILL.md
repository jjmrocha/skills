---
name: analyze-code
description: Use when auditing existing code — "review my changes", "check this PR", "look at the diff", code review, security review of a branch, cleanup or duplication pass, legacy reviews, pre-PR self-review, module health checks, or tech-debt assessment before a large change.
---

# Analyze Code

Multi-lens audit of existing code: five specialist perspectives produce candidate findings, an independent verify pass adjudicates them, and the survivors ship as a prioritized report — a deep review, not a gate decision.

Report-only. This skill never applies fixes; it routes them.

**If the conversation was compacted, re-invoke this skill before continuing.**

## When NOT to Use

- Writing new code → `using-software-specialists`
- Diagnosing a specific bug → `using-software-specialists` with `troubleshooter`

## The Five Lenses

| Lens | What it covers | Reference |
|------|----------------|-----------|
| **Architecture** | Coupling, layering, public-API contracts, cohesion, deploy topology, runtime concerns (graceful shutdown, signals, healthchecks, retry/backoff) | `system-architect` specialist |
| **Quality** | Three named angles — Simplification, Efficiency, Altitude (see Step 5) — plus test-coverage signal, CI/IaC config quality (Dockerfile, Makefile, GH Actions), 12-factor config | `refactoring-expert` specialist |
| **Performance** | Hot paths, algorithmic complexity, N+1, unnecessary allocations | `performance-engineer` specialist |
| **Security** | Input trust, auth, supply-chain (lockfiles, pinned base images, vuln scanners), secrets (env hygiene, KMS/Vault refs, log/layer leakage), license/SBOM | `security-engineer` specialist |
| **Style** | Language style guide and formatting | `style-checker` skill |

Apply **all five** — single-lens audits miss cross-cutting issues. Each lens loads its specialist from `using-software-specialists`; the lens questions are a starting point, not a substitute. Exception: the Style lens runs via the `style-checker` skill.

## Severity Scale

| Severity | Definition |
|----------|-----------|
| **Critical** | Data loss, security breach, or outage risk (SQLi, hardcoded secret, auth bypass, race in state writes) |
| **High** | Significant bug or smell with downstream blast radius (N+1 in hot path, missing input validation, god class) |
| **Medium** | Maintainability debt or anti-pattern (high complexity, missing edge-case tests) |
| **Low** | Style, naming, magic numbers — non-blocking |

Don't inflate severity. Low stays Low. Reserve Critical for real blast radius.

## Workflow

1. **Scope & Boundary Frame** — pin down what's being audited.
   - **Scope:** PR mode = `git diff origin/main...HEAD`; module/repo mode = the path the user passed. Record in the report header.
   - **Skip rules:** auto-generated, vendored, build-output, minified — see [references.md](references.md). File presence is still a signal.
   - **If `kb_path` configured:** load `knowledge-base` first. Wiki↔code disagreements are findings per `knowledge-base` Integration rules.

2. **Intent conformance** (skip if no spec and no plan) — gather intent from two sources: a spec/ticket the user provided, and the implementation plan in the KB plans dir (if `kb_path` is configured and one exists). For each stated requirement or acceptance criterion, locate where the code satisfies it; for each plan step, confirm it was implemented.
   - **Unmet requirement** (asked/planned but not delivered) = **High**; **Critical** if it's a correctness/security guarantee.
   - **Undocumented deviation** (built differently from the plan, no ADR/note explaining why) = **Medium**.
   - **Scope creep** (delivered but never asked for) = **Low**, unless it adds blast radius (new endpoint, new dependency), then **Medium**.
   - If no spec and no plan exist, state that in the report and skip — do not invent acceptance criteria.

3. **Breaking-change scan** (modified code only) — for each changed signature, return type, raised error, side effect, or invariant on an existing symbol, list every caller via `find_referencing_symbols` or `grep`, verify the new contract holds at each call site, and report any caller that breaks as a finding. Public-API breaks are Critical/High; a single internal caller is Medium. Skip on greenfield.

4. **Convention & duplication scan** (new or modified code only) — skip on greenfield. This step is the `coding-discipline` Parallel-Solution test applied as an audit. Both halves run.

   **4a. Establish the baseline.** Drift is measured against a source, not against taste. Before judging anything, collect what actually governs the changed code:
   - Every governing `CLAUDE.md`: user-level `~/.claude/CLAUDE.md`, the repo root, and any `CLAUDE.md` / `CLAUDE.local.md` in a directory that is an ancestor of a changed file — a directory's file governs only files at or below it.
   - If `kb_path` is configured: the `patterns/` pages covering the touched surface.
   - The two or three nearest sibling files to each changed file — where nothing is written down, the local idiom *is* the standard.

   Flag a convention violation only when you can **quote the rule and quote the line that breaks it**, naming the source. No "spirit of the doc" inferences, no personal preference. If nothing governs the changed code, say so and flag nothing here.

   **4b. Duplication — make the claim checkable.** Two rules carry this half:

   - **Name the incumbent.** Every duplication finding names the existing symbol, at `file:line`, that should be called instead. A finding that cannot name one is not a duplication finding — drop it, or downgrade it to convention drift.
   - **State what you searched.** "No equivalent found" is credible only with the searches named — an unstated search is an unrun search. This applies hardest to the non-findings: say why the new helper you *didn't* flag has no incumbent.

   Search by behavior, not by name. The question is *does this repo already solve this problem class?*, not *does this name already exist?*. Duplicate code rarely shares a name with what it duplicates — that is why it got written — so an empty name search is not evidence the duplicate is absent.

   If the repo's shared and utility modules are small enough to read end to end, read them; that settles the question directly and no search strategy is needed. When they are not, run **at least two** of:
   - **Signature shape** — `find_symbol` for functions taking the same parameter types and returning the same type, regardless of name.
   - **Callee fingerprint** — grep the distinctive API, constant, regex, or library call it wraps. Two solutions to the same problem call the same underlying things.
   - **Problem-class sweep** — for the known classes (pagination, validation, auth, retry/backoff, error mapping, config loading, logging, serialization, date/ID formatting), go straight to the module that owns the class.
   - **Domain vocabulary** — grep the nouns of the new code's domain, not its function name.

   Severity: parallel implementation of an existing solution = **High**; convention violation with a quoted rule = **Medium**; local idiom inconsistency = **Low**.

5. **Apply the five lenses** — Architecture, Quality, Performance, Security, Style, each covering its row in the Five Lenses table above against the scoped code. Directives beyond the table:
   - **Architecture:** also check cross-service consistency where the changed code crosses service or package boundaries.
   - **Quality:** run three named angles, each producing findings that name the concrete cost (what is duplicated, wasted, or made harder to maintain) rather than a vague smell. Reuse is not here — Step 4b owns it.
     - **Simplification** — unnecessary complexity the change adds: redundant or derivable state, copy-paste with slight variation, deep nesting, dead code left behind. **Name the simpler form that does the same job.**
     - **Efficiency** — wasted work the change introduces: redundant computation or repeated I/O, independent operations run sequentially, blocking work added to startup or a hot path. Also long-lived objects built from closures or captured environments — they hold the entire enclosing scope alive for the object's lifetime, which leaks when that scope holds large values; prefer a struct or class copying only the fields it needs. **Name the cheaper alternative.**
     - **Interface depth** — for each new or widened interface, what must the caller now know (types, constants, invariants) versus what does the module hide? A method that returns stored state and hides nothing widens the surface for free-looking reasons — a zero-line diff in the implementer is not evidence the change was free. Load `designing-interfaces`. **Name the behavior that should have moved behind the interface.**
     - **Altitude** — is each change made at the right depth, or is it a bandaid? Special cases layered onto shared infrastructure signal that the fix isn't deep enough; prefer generalizing the underlying mechanism. **Name the level the fix belongs at.**
   - **Performance:** report what the code reveals; don't flag missing profiling as a defect.
   - **Security:** hardcoded secrets are Critical; a missing rotation/Vault reference where one is expected is High. **Apply the exclusions and precedents in [references.md](references.md) before emitting any security finding** — they suppress the known false-positive classes.
   - **Style:** load `style-checker` — it owns linter discovery, severity mapping, and conflict-resolution.

6. **Run configured tooling** — for every linter, formatter, scanner, or test suite the project ships, **you must run it — "looked at the code" is not a substitute**.
   - **Discovery path:** See [references.md](references.md) for the full ordering.
   - **Per file-type scanners:** Full matrix in [references.md](references.md).
   - Fold tool failures into findings at their natural severity (failing security test → Critical; lint nit → Low). Tooling configured but currently red is itself a finding. **Tooling configured but not invoked by CI is a Medium "CI hygiene" finding.** No tooling configured at all where relevant files exist is the same severity.
   - **Test suite execution:** report pass/fail counts, skipped-test list, and **new failures vs. the base SHA**. Flakiness analysis and perf timing are out of scope (use the `verify` skill).

7. **Verify** — everything Steps 2–5 produced is a *candidate*, not a finding.

   Dedup candidates pointing at the same line and mechanism, keeping the one with the most concrete evidence. Then adjudicate each survivor with **one verifier subagent** that has not seen the finder's reasoning — independence is the whole mechanism; a self-check in the same context only re-confirms itself. Each verifier returns exactly one verdict:

   - **Confirmed** — can name the inputs or state that trigger it and the resulting wrong outcome. Quotes the line.
   - **Plausible** — the mechanism is real but the trigger is uncertain (timing, environment, config). States what would confirm it.
   - **Refuted** — factually wrong (quote the actual line); provably impossible (show the type, constant, or invariant); already handled elsewhere (cite the guard); or pure style with no observable effect.

   **The verifier inherits the finder's reference.** A verifier given only the diff cannot check a claim that was never about the diff, and will refute it for lack of evidence — which would destroy exactly the checks this skill is best at. So: intent-conformance candidates ship with the spec or plan excerpt; breaking-change candidates ship with the caller list from Step 3; duplication candidates ship with the incumbent symbol from Step 4b; convention candidates ship with the quoted rule and its source path. **No reference, no verdict** — a verifier that cannot check the claim returns Plausible, never Refuted.

   **Plausible by default.** Do not refute a candidate for being "speculative" or "dependent on runtime state" when that state is realistic: concurrency races, nil on a rare-but-reachable path (error handler, cold cache, absent optional field), falsy-zero treated as missing, off-by-one on a boundary the code does not exclude, retry storms, partial failures, an allowlist that lost its anchor. Refute only what you can refute *from the code*.

   Keep Confirmed and Plausible; drop Refuted. **The verdict is the `Confidence` value in the report schema** — never assert confidence without a verifier verdict behind it.

   **Not verified:** Step 6 tool output. A linter error or a failing test is ground truth and goes straight to the report.

   If the `Agent` tool is unavailable, verify each candidate yourself, sequentially, re-deriving it from its reference rather than from your earlier reasoning — and say in the report that verification was single-pass, so nobody is misled about what ran.

8. **Synthesize & deliver** — group, dedupe, rank by severity. Tag each finding `scope: system` or `scope: code`. Output two severity-ordered lists: **System-level findings** then **Code-level findings**. Cap Low at 10 per lens and Medium at 15 per lens; if hit, emit a meta-finding noting the truncation. Critical/High are uncapped.

## False-Positive Markers

Documented intent downgrades or drops a finding. Cite the marker as evidence when adjusting:

- `// nolint:<rule>` / `# noqa: <rule>` with a comment giving the reason
- `unsafe` blocks (Rust) or `// SAFETY:` comments stating the invariant
- ADR-cited deviations from a `patterns/<name>.md` page
- Documented perf hacks with a benchmark reference

Undocumented suppressions stay at original severity — the absence of rationale is itself the smell.

## Report Template

```markdown
# Analysis: <target>

**Analyzed-SHA:** <commit>
**Scope:** <paths or `git diff origin/main...HEAD`>

**Tools:**

| tool | version | status | reason-if-skipped |
|------|---------|--------|-------------------|
| ruff | 0.6.3 | ran (3 warnings) | |
| gitleaks | — | skipped | not installed |
| trivy | 0.50 | failed (2 CVEs) | |

**Summary:** <1-2 sentences — headline findings>

## Priority Actions
1. [Critical|High] <action> — <file:line>

## Intent Conformance
<Source: spec/ticket provided | plan at <path> | none — skipped>
- [Met | Unmet | Deviation | Scope-creep] <requirement or plan step> — <file:line or "not found">

## System-level Findings
- [Severity · Confirmed|Plausible · root-cause|symptom] <Finding> — <file:line>
  - Evidence: <snippet or reference>
  - Impact: <consequence>
  - Action: <fix> → <specialist>

## Code-level Findings
- [Severity · Confirmed|Plausible · root-cause|symptom] <Finding> — <file:line>
  - Evidence: <snippet>
  - Impact: <consequence>
  - Action: <fix> → <specialist>

## Tests
- Pass: <n>  Fail: <n>  Skipped: <n>
- New failures vs <base-SHA>: <list>
- Skipped tests: <list of test IDs>

## Coding Style
<Summary; reference the style-checker report for full detail.>

## Suggested Next Actions
- **Critical / High** → re-enter `using-software-specialists` with the matching specialist. Routing table in [references.md](references.md). One fix loop per finding cluster.
- **Medium** → ticket or batch into a planned cleanup, or address now if the cluster is cheap.
- **Low** → optional inline fix, batch with the next touch of the file, or accept.
```

Findings are severity-ordered within each section; lenses are internal scaffolding. The "Suggested Next Actions" block closes the audit → fix loop. Don't invent new severities to fill the block — if there are no Critical/High findings, say so.

## Example: good vs bad finding

**Good** — actionable, evidenced, routed:

```
- [Critical · Confirmed · root-cause] Hardcoded JWT signing key — auth/jwt.py:42
  - Evidence: `SECRET = "shared-secret-123"` (committed in 5401b49)
  - Impact: anyone with repo access can forge tokens; rotation requires a redeploy
  - Action: move to KMS-backed env var; switch HS256 → RS256 → Security Engineer
```

**Bad** — unactionable, no evidence, no routing:

```
- [High] consider better security — auth.py
```

The bad form is unusable: no file:line, no confidence, no scope, no evidence, no specialist. Don't ship findings like this.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Applying one lens only | All five — cross-cutting issues hide between lenses |
| Lens-grouped output | Two sections (System / Code), each severity-ordered |
| Inflating severity | Reserve Critical for real blast radius |
| **Deflating severity to avoid rework** | Critical stays Critical even when the fix is expensive — that's why it's Critical |
| Reporting non-findings | Skip "profiling wasn't done" — focus on what the code reveals |
| Treating convention drift as a style nit | Convention drift is Medium, not Low |
| Findings without file:line / evidence / specialist | Use the schema; ship the bad-finding form and the audit is wasted |
| Honoring an undocumented `nolint` | Suppression without a stated reason stays at original severity |
| **Asserting `Confidence` without a verifier verdict** | Run Step 7 — self-assessed confidence is the finder marking its own work |
| **Searching for duplicates by name** | Duplicates rarely share a name with what they duplicate. Search by behavior (Step 4b) |
| **"No existing equivalent found" with no searches named** | An unstated search is an unrun search. List what you ran |
| **A duplication finding that names no incumbent** | Not a duplication finding. Drop it or downgrade to convention drift |
| **Convention drift judged against taste** | Quote the rule and its source (Step 4a), or don't flag it |
| **Refuting a candidate the verifier had no reference for** | No reference, no verdict — return Plausible, never Refuted |
