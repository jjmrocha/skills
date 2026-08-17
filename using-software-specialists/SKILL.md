---
name: using-software-specialists
description: Use when starting any non-trivial software task — feature, bugfix, refactor, migration, security/auth work, performance work, or turning a spec into a plan — before writing code, diagnosing, or proposing a fix.
---

# Using Software Specialists

**Core principle:** Every software task touches multiple domains. Each specialist asks a question the others don't — skipping one means that question never gets asked.

**If the conversation was compacted, re-invoke this skill before continuing.**

## When NOT to Use

| Don't load when... | Instead... |
|---|---|
| Pure copy/paste, rename, typo, comment-only change | Just do it |
| Single-line edit you already verified touches no auth, payment, schema, or public API | Just do it |
| The relevant specialist was already applied this session for the same surface | Reuse the prior framing |

## Phases

**Requirements** (what?) → **Design** (shape?) → **Plan** (order?) → **Implementation** (how?) → **Testing** (works?) → **Validation** (safe?) → **Documentation** (maintains?)

Advance only when the current phase's output is complete:

| Phase | Done when... |
|------|--------------|
| Requirements | Acceptance criteria testable, scope exclusions explicit, NFRs listed |
| Design | Component boundaries defined, data model serves all access patterns, API contracts written |
| Plan | Tasks decomposed, dependencies explicit, riskiest work first, verification check per step |
| Implementation | Feature works end-to-end (not just compiles), each behavior driven by a test written first, error/loading/empty states handled, contracts honored |
| Testing | Edge cases enumerated and covered beyond the TDD suite, test levels right (inverted pyramid), no flaky tests, tests pass in CI not just locally |
| Validation | Security review passed, QE strategy confirmed, "Validate Before Done" answered |
| Documentation | Public APIs/READMEs/runbooks updated, owner assigned, outdated docs deleted |

Backend and Frontend implementation can run in parallel against an agreed API contract — the contract is the seam.

**Testing is not "after" coding.** Tests are written test-first *during* Implementation (TDD). The Testing phase hardens that suite — edge cases, test levels, flakiness, CI — it never starts the testing.

**Implementation:** load `coding-discipline` and `test-driven-development`. If `kb_path` is configured, also load `knowledge-base` first.

**If the user provides a plan file** (e.g., *"plan and implement using ~/plans/X.md"*), read it first and validate it against the Plan row's done-criteria above. Surface gaps and stop if any are missing — do not start coding against an incomplete plan.

## Task Routing

Forward lookup by task domain. "Start with" = lead mindset. "Then add" = complementary perspectives during/after implementation. "Before done" = validation gate, never skip.

**Applying a specialist means reading its reference file first: `references/<specialist>.md`.** The name alone is not the specialist — the file carries its required sub-skills, focus areas, and red flags. Role-playing from the table row without reading the file is skipping the specialist.

| Task | Start with | Then add | Before done |
|------|-----------|----------|-------------|
| Backend development (APIs, server logic, caching) | Backend Engineer | Tester | Security Engineer, Quality Engineer |
| Data modeling, schema design, migrations, indexing | Database Designer | Backend Engineer | Security Engineer, Quality Engineer |
| Frontend development (UI, state, accessibility, performance) | Frontend Engineer | Tester | Security Engineer, Quality Engineer |
| New service or system design | System Architect | Backend Engineer, Database Designer | Security Engineer, Quality Engineer |
| Full-stack feature | System Architect | Backend Engineer, Database Designer, Frontend Engineer, Tester | Security Engineer, Quality Engineer |
| Auth, security, compliance, threat modeling | Security Engineer | Backend Engineer | Quality Engineer |
| Test strategy, quality gates, flaky tests, inverted pyramid | Quality Engineer | Tester | — |
| Writing unit/integration tests for specific code | Tester | — | Quality Engineer |
| CI/CD, deployment, infra, monitoring | DevOps Engineer | — | Security Engineer, Quality Engineer |
| Code quality, refactoring, technical debt | Refactoring Expert | Tester | Quality Engineer |
| Bug, build failure, deploy failure, regression after a change | Troubleshooter | Performance Engineer (if perf-related) | Quality Engineer |
| Performance tuning, profiling, capacity planning, load testing | Performance Engineer | Backend Engineer, Database Designer, Frontend Engineer (if FE/Core Web Vitals) | Quality Engineer |
| New project, requirements, scoping, PRDs | Requirements Analyst | — | — |
| Turning an approved spec into an execution plan | Project Planner | — | — |
| Technical investigation, research, analysis | Deep Research Agent | — | — |
| Documentation, user guides, API references | Technical Writer | — | — |
| Prompt optimization, few-shot design, LLM eval, prompt-cache layout, long-context strategy | Prompt Engineer | — | Security Engineer |
| LLM-powered feature, AI agent, RAG pipeline, AI-assisted action | Prompt Engineer | ML Engineer (if retrieval/embeddings), Backend Engineer | Security Engineer, Quality Engineer |
| ML training, fine-tuning, model evaluation, retrieval/embedding design, fairness/bias audit | ML Engineer | Prompt Engineer (if LLM), Backend Engineer (if pipeline) | Security Engineer, Quality Engineer |

**Minimum rule:** Security Engineer + Quality Engineer must appear in "Before done" for any task that touches APIs, user data, or production code.

## Disambiguating Specialists

When two specialists could both fire, each asks a unique question — see [references/specialist-questions.md](references/specialist-questions.md). Load it before invoking a specialist whose role you're unsure of.

### Tester vs Quality Engineer

- **Tester** = craftsperson: edge cases, mock boundaries, assertion clarity for *this* code. Writes good tests during implementation.
- **Quality Engineer** = strategist: right test level, testability of the design, inverted pyramid, flaky-test erosion. Validates the strategy before done.

**The "systematic coverage" trap:** Edge-case enumeration for a specific function — null inputs, boundaries, invalid types, overflow — IS Tester work even when it feels systematic. QE owns the *level*, not whether you've covered all cases for *this function*. "Write tests for `calculateDiscount()`" → Tester leads.

## Validate Before Done

Answer each item that applies before marking complete. Security and QA are universal; the rest trigger on their condition.

- **Security** *(always)*: What inputs are trusted? What can be abused? Is auth enforced?
- **QA** *(always)*: What edge cases are untested? What fails under bad input or load?
- **Troubleshoot** *(if you debugged)*: Root cause confirmed, or just the symptom patched?
- **Refactor** *(if you changed existing code)*: All existing behavior preserved? Tests still passing?
- **Docs** *(if anything user/operator-facing changed)*: APIs / READMEs / runbooks updated? Owner assigned?

## Anti-Patterns

Routing rationalizations only — process discipline lives in `coding-discipline`.

| If you think... | Reality |
|---|---|
| "The 'Start with' specialist is enough" / "Validate is optional" / "It's internal, no security concerns" | "Then add" and "Before done" columns are non-negotiable gates. Internal APIs still have auth gaps, injection, and trust-boundary risks. |
| "Existing tests still pass after the auth refactor, ship it" | Auth bugs don't fail tests — they create bypass paths your tests weren't written to catch. Auth refactors always require Security Engineer review regardless of test results. |

When a specialist spots an issue outside their domain, flag it explicitly for the relevant specialist — don't silently ignore cross-domain concerns.
