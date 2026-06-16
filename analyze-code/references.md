# analyze-code — references

Heavy reference material for `analyze-code`. Load on demand from Step 6 or when a finding needs the detail.

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
