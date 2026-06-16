---
name: analyze-code
description: Use when auditing existing code — "review my changes", "check this PR", "look at the diff", legacy reviews, pre-PR self-review, module health checks, or tech-debt assessment before a large change.
---

# Analyze Code

Multi-lens audit of existing code: five specialist perspectives produce a prioritized findings report — a deep review, not a gate decision.

**If the conversation was compacted, re-invoke this skill before continuing.**

## When NOT to Use

- Writing new code → `using-software-specialists`
- Diagnosing a specific bug → `using-software-specialists` with `troubleshooter`

## The Five Lenses

| Lens | What it covers | Reference |
|------|----------------|-----------|
| **Architecture** | Coupling, layering, public-API contracts, cohesion, deploy topology, runtime concerns (graceful shutdown, signals, healthchecks, retry/backoff) | `system-architect` specialist |
| **Quality** | Complexity, duplication, test-coverage signal, CI/IaC config quality (Dockerfile, Makefile, GH Actions), 12-factor config | `refactoring-expert` specialist |
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

4. **Convention & duplication scan** (new or modified code only) — apply `coding-discipline` Parallel-Solution test: for each new helper, type, or pattern, `find_symbol`/`grep` for an existing equivalent first. Parallel implementation = **High**; convention drift = **Medium**; minor inconsistency = **Low**. Skip on greenfield.

5. **Apply the five lenses** — Architecture, Quality, Performance, Security, Style, each covering its row in the Five Lenses table above against the scoped code. Directives beyond the table:
   - **Architecture:** also check cross-service consistency where the changed code crosses service or package boundaries.
   - **Performance:** report what the code reveals; don't flag missing profiling as a defect.
   - **Security:** hardcoded secrets are Critical; a missing rotation/Vault reference where one is expected is High.
   - **Style:** load `style-checker` — it owns linter discovery, severity mapping, and conflict-resolution.

6. **Run configured tooling** — for every linter, formatter, scanner, or test suite the project ships, **you must run it — "looked at the code" is not a substitute**.
   - **Discovery path:** See [references.md](references.md) for the full ordering.
   - **Per file-type scanners:** Full matrix in [references.md](references.md).
   - Fold tool failures into findings at their natural severity (failing security test → Critical; lint nit → Low). Tooling configured but currently red is itself a finding. **Tooling configured but not invoked by CI is a Medium "CI hygiene" finding.** No tooling configured at all where relevant files exist is the same severity.
   - **Test suite execution:** report pass/fail counts, skipped-test list, and **new failures vs. the base SHA**. Flakiness analysis and perf timing are out of scope (use the `verify` skill).

7. **Synthesize & deliver** — group, dedupe, rank by severity. Tag each finding `scope: system` or `scope: code`. Output two severity-ordered lists: **System-level findings** then **Code-level findings**. Cap Low at 10 per lens and Medium at 15 per lens; if hit, emit a meta-finding noting the truncation. Critical/High are uncapped.

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
- [Severity · Confidence · root-cause|symptom] <Finding> — <file:line>
  - Evidence: <snippet or reference>
  - Impact: <consequence>
  - Action: <fix> → <specialist>

## Code-level Findings
- [Severity · Confidence · root-cause|symptom] <Finding> — <file:line>
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
