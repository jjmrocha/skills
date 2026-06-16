---
name: style-checker
description: "Use when checking, reviewing, or auditing code style, formatting, or naming conventions — even if the user just says 'check my code style' or 'does this follow Google style'."
---

# Google Style Checker

Reviews code against Google's official style guidelines for **formatting and naming only**. Does not check logic, architecture, or code quality (SOLID, smells). Does not auto-fix — reports violations to fix.

**Supported languages:** Go, Java, Python, JavaScript, TypeScript, Shell, Markdown.

## Workflow

**When invoked from `analyze-code`:** return a flat findings list (severity + file:line + rule). Skip the full report template in Step 4 — the outer audit owns the report shape.

### Step 1: Identify languages and load references

Scan the repo (or the path the user provided) and, for each supported language present, load its reference file **before** scanning code.

| Language | Reference file | Detection |
|----------|---------------|-----------|
| Python | [references/python.md](references/python.md) | `*.py` |
| Java | [references/java.md](references/java.md) | `*.java` |
| JavaScript | [references/javascript.md](references/javascript.md) | `*.js`, `*.jsx`, `*.mjs` |
| TypeScript | [references/typescript.md](references/typescript.md) | `*.ts`, `*.tsx` |
| Go | [references/go.md](references/go.md) | `*.go` |
| Shell | [references/shell.md](references/shell.md) | `*.sh`, `*.bash` |
| Markdown | [references/markdown.md](references/markdown.md) | `*.md` |

**Always skip:** `vendor/`, `node_modules/`, `.git/`, `*.pb.go`, `*_generated.go`, and any file whose first lines contain `// Code generated` or `# Generated`. **Deprioritize** test/spec files (`*_test.go`, `*.spec.*`, `test_*.py`) unless the user explicitly asks to include them.

If no supported-language files are detected, report this and exit.

### Step 2: Advisor mode (optional)

If the user asks a style question rather than requesting a scan (e.g., "how should I name constants in Go?"), answer directly from the loaded reference. You can also answer, then offer to scan relevant files.

### Step 3: Scan for violations

For each file, check against the reference rules. Focus on:
- Naming conventions (case style for identifiers, packages, files)
- Formatting (indentation, line length, brace style)
- Import/module organization
- Comment and documentation style

### Step 4: Produce the report

```
# Google Style Check Report

## Summary
- Files scanned: N
- Languages: [list]
- Total violations: N (Critical: N, High: N, Medium: N, Low: N)

## Critical
### <Language>
- `path/to/file.go:12` — **Rule**: Expected `lowerCamelCase` for unexported function, found `my_Function`

## High
### <Language>
- `path/to/file.py:45` — **Rule**: Class names must use `CapWords`, found `my_class`

## Medium
### <Language>
- `path/to/file.java:88` — **Rule**: Line exceeds 100 characters (found 117)

## Low
### <Language>
- `path/to/file.ts:10` — **Rule**: Use `import type` for type-only imports

## Clean files
List any files with zero violations. Omit this section if all files have violations.
```

## Severity Classification

| Severity | What it covers |
|----------|---------------|
| **Critical** | Wrong exported/unexported casing in Go; tabs vs spaces; fundamental structure violations |
| **High** | Wrong case style for identifiers (classes, functions, constants, variables) |
| **Medium** | Line length, indentation size, brace placement, import ordering |
| **Low** | Comment formatting, blank lines, minor whitespace, optional style preferences |

## Tips

- If a file has many violations of the same rule, report the first 3 occurrences and note "and N more".
- Go projects: `gofmt` compliance is the source of truth — note if running `gofmt` would auto-fix issues.
- See [expected_outputs/sample-report.md](expected_outputs/sample-report.md) for a full example.

## Common Mistakes

- **Wrong severity for Go constants**: `UPPER_SNAKE_CASE` in Go is **Critical** (breaks the fundamental MixedCaps rule), not High.
- **Scanning generated or vendored code**: the Step 1 skip list is mandatory, not optional.
- **Reporting test/spec files when not asked**: when the user says "check my code", they almost always mean source files — deprioritize tests unless explicitly requested.
