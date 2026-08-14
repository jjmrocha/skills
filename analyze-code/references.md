# analyze-code — references

Heavy reference material for `analyze-code`. Load the security exclusions from Step 5, the tooling and skip-path sections from Step 6, or any section when a finding needs the detail.

## Tooling discovery paths

When Step 6 runs, search for the project's authoritative command list in this order. First match wins, but check all sources if rules conflict:

1. `.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`, `buildkite/pipeline.yml` — CI workflows
2. `Makefile`, `justfile`, `Taskfile.yml` — task runners
3. `package.json` `scripts`, `pyproject.toml` `[tool.*]`, `tox.ini`, `noxfile.py` — language-native
4. `.pre-commit-config.yaml` — git hook tools
5. `README.md` / `CONTRIBUTING.md` as a tiebreaker

A repository with relevant source files but no command list in any of the above is itself a Medium "CI hygiene" finding.

A command list that exists in `Makefile` / `package.json` / `pyproject.toml` but is **not** invoked by any CI workflow is the same severity (Medium) — "configured but CI doesn't run it" — surfaced as a separate finding.

## Per file-type scanners

Trigger these when the listed file type appears in scope. Run each that is installed locally; record the result in the report header `tools` table.

| File type | Scanners |
|---|---|
| `Dockerfile`, `*.dockerfile` | `hadolint`, `trivy image`, `dive` |
| `*.tf`, `*.tfvars` | `tfsec`, `checkov`, `terraform validate` |
| `*.yml` / `*.yaml` (k8s manifests) | `kube-linter`, `kubeconform`, `checkov` |
| Helm chart | `helm lint`, `kubeconform`, `checkov` |
| Lockfiles (`package-lock.json`, `poetry.lock`, `go.sum`, `Cargo.lock`) | `osv-scanner`, `npm audit`, `pip-audit`, `govulncheck`, `cargo audit` |
| Any text file | `gitleaks` (secret scan), `semgrep` (custom rule sets) |
| Any source file | the project's language linter (delegated to `style-checker`) |

If a project ships relevant files but none of these scanners is configured or installed, the absence is itself a Medium finding (Step 6 "no tooling configured" rule).

## Skip-path patterns

Exclude these from per-file analysis. File **presence** and version pinning remain signals for the supply-chain checks; the **contents** are skipped.

- Dependency directories: `node_modules/`, `vendor/`, `.venv/`, `target/`
- Build output: `dist/`, `build/`, `out/`, `.next/`, `.nuxt/`
- Generated code: `*.pb.go`, `*_pb2.py`, `*_pb2_grpc.py`, `*_generated.*`, `*.gen.go`, `*.g.dart`
- Minified bundles: `*.min.js`, `*.min.css`
- Lockfile **contents** (the file's existence is still a Step 6 signal)

A finding inside a skipped path is only valid if the user explicitly asked for the path to be analyzed.

## Security lens — exclusions and precedents

Load from Step 5 before emitting any security finding. These suppress the known false-positive classes; without them the Security lens floods the report with theoretical issues and the real ones get lost.

**Scope.** These govern *judgment-derived vulnerability claims* — a human reading code and reasoning about exploitability. They do **not** override the Security lens's supply-chain, secret-hygiene, and license checks, or any scanner result from Step 6. A `gitleaks` hit or a `trivy` CVE is tool output and reports at its natural severity regardless of what follows.

**Confidence bar.** Only claim a vulnerability at ≥80% confidence of real exploitability. Below that, drop it — do not hedge it into the report as Low.

**Hard exclusions** — never report as a vulnerability:

1. Denial of service, resource exhaustion, memory/CPU consumption, rate limiting.
2. Regex injection and regex-based DoS.
3. Missing hardening. Code isn't expected to implement every best practice — flag concrete vulnerabilities, not absent defenses.
4. Theoretical race conditions and timing attacks. Report a race only when concretely problematic.
5. Memory-safety issues (buffer overflow, use-after-free) in memory-safe languages — Rust, Go, Java, Python, JS.
6. Findings in test-only files and fixtures.
7. Log spoofing. Unsanitized user input reaching logs is not itself a vulnerability.
8. SSRF where only the URL *path* is controlled — SSRF requires control of host or protocol.
9. User-controlled content placed in an LLM system prompt.
10. Findings in documentation and markdown files.
11. Absence of audit logging.
12. Missing input validation on non-security-critical fields with no demonstrated security impact.

**Precedents** — settled calls, don't relitigate:

1. Environment variables and CLI flags are **trusted**. An attack requiring the attacker to set one is invalid.
2. UUIDs are unguessable and need no validation.
3. React and Angular escape by default — no XSS finding in `.jsx`/`.tsx`/Angular templates unless the code uses `dangerouslySetInnerHTML`, `bypassSecurityTrustHtml`, or an equivalent escape hatch.
4. Client-side JS/TS is untrusted by definition. Missing authn/authz checks there are not vulnerabilities — the server owns validation.
5. Logging secrets, passwords, or PII in plaintext **is** a vulnerability. Logging URLs or non-PII data is not, even when the data feels sensitive.
6. Low-impact web issues — tabnabbing, XS-Leaks, prototype pollution, open redirects — only at very high confidence.
7. GitHub Actions and Jupyter notebooks: most findings aren't exploitable in practice. Require a specific attack path from genuinely untrusted input.
8. Resource leaks (memory, file descriptors) are quality findings for the Quality lens, not security findings.

A finding that survives all of the above still needs the standard schema: `file:line`, evidence, a concrete exploit path, and the fix. "Could be vulnerable" is not a finding.

## Specialist routing for `Suggested Next Actions`

Map each finding cluster to one specialist for the `using-software-specialists` handoff. Use the lowest row that fits.

| Finding cluster | Specialist |
|---|---|
| Auth, input validation, secrets, crypto, supply-chain, license | Security Engineer |
| Logic, idempotency, error handling, control flow | Backend Engineer |
| Schema, indices, queries, migrations | Database Designer |
| Hot path, allocations, N+1, profiling | Performance Engineer |
| Structural debt, complexity, duplication, naming | Refactoring Expert |
| Deploy topology, runtime, CI/IaC, healthchecks, signals | DevOps / Platform Engineer |
| Cross-service contract, public-API design, layering | System Architect |

If a finding spans two specialists, route to the one that owns the **highest-blast-radius** dimension — typically Security or System Architect.
