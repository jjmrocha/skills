#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""
Lint a knowledge base: walk every page under `wiki/`, `plans/`, and `manuals/`,
run seven mechanical checks, emit a report. The agent acts on the report instead
of loading every page.

Run from inside a repo's working tree. In-tree source-liveness is checked
against the current repo (`git rev-parse --show-toplevel`). Pages belonging to
a different repo have their path sources marked "cross-repo, not checked."

KB layout:
    <kb_path>/
      wiki/                   per-repo system docs
        index.md
        <repo>/
          index.md
          entities/ interfaces/ jobs/ dependencies/ events/ rules/
      plans/                  implementation plans
        index.md
        <ticket-or-branch>.md
      manuals/                operator-facing documentation
        index.md
        <topic-slug>.md

Run:
    uv run scripts/lint.py <kb_path>
    uv run scripts/lint.py <kb_path> --json   # parseable; preferred for agents

Checks:
    1. Broken `sources:` paths (in-tree only; rename detection via git log)
    2. Aging pages (last_updated > 90 days)
    3. Orphan pages (no inbound [[wiki-link]])
    4. Concept-gap candidates (regex heuristic; expect false positives)
    5. [needs source] markers
    6. All in-tree sources dead — auto-delete, or flag when protected
       (plans and manuals are never auto-deleted)
    7. `kind:` validity (pages under patterns/ and manuals/ must declare kind)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml


WIKI_LINK_RE = re.compile(r"\[\[([^\]\[]+)\]\]")
NEEDS_SOURCE_RE = re.compile(r"\[needs source\]", re.IGNORECASE)
CONCEPT_RE = re.compile(
    r"\bthe\s+([a-z][a-z0-9_-]*)\s+"
    r"(table|service|event|job|endpoint|topic|rule)\b",
    re.IGNORECASE,
)
TYPE_TO_SUBFOLDER = {
    "table": "entities",
    "service": "dependencies",
    "event": "events",
    "topic": "events",
    "job": "jobs",
    "endpoint": "interfaces",
    "rule": "rules",
}
AGING_DAYS = 90
VALID_PATTERN_KINDS = {"convention", "recipe", "template"}
VALID_MANUAL_KINDS = {"how-to", "explainer"}
PROTECTED_BUCKETS = {"plans": "plan", "manuals": "manual"}


@dataclass
class Page:
    rel_path: str
    abs_path: Path
    frontmatter: dict
    body: str
    outbound_links: set[str] = field(default_factory=set)
    repo: str | None = None
    scope_repos: list[str] | None = None


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from the body. Returns ({}, text) if absent.

    Normalizes BOM and CRLF before parsing so pages saved on Windows or pasted
    from a browser don't silently bypass every check by being treated as
    bodyless.
    """
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        return {}, text
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5:]
    try:
        meta = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def detect_page_repo(rel_path: str) -> str | None:
    """Return the repo name from a page's KB-relative path.

    Pages under wiki/<repo>/... → repo is <repo>.
    Pages under plans/..., manuals/..., or wiki/index.md → None.
    """
    parts = rel_path.split("/")
    if len(parts) >= 3 and parts[0] == "wiki":
        return parts[1]
    return None


def detect_manual_scope(rel_path: str, frontmatter: dict) -> list[str] | None:
    """Return the repos a manual page is scoped to, or None.

    Manuals live flat under `manuals/` and declare their scope in `repos:`.
    None means "not a manual" or "whole-system manual" — both are checked
    against whatever repo the agent is currently in, same as a plan.
    """
    if not rel_path.startswith("manuals/"):
        return None
    repos = frontmatter.get("repos")
    if not isinstance(repos, list) or not repos:
        return None
    return [str(r).strip() for r in repos]


def protected_bucket(rel_path: str) -> str | None:
    """Return 'plan' or 'manual' for pages that are never auto-deleted."""
    return PROTECTED_BUCKETS.get(rel_path.split("/")[0])


def walk_kb(kb_path: Path) -> list[Page]:
    """Load every .md page under `kb_path` into a list of Page objects."""
    pages = []
    for md in sorted(kb_path.rglob("*.md")):
        rel = md.relative_to(kb_path).as_posix()
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm, body = parse_frontmatter(text)
        links = {m.group(1).strip() for m in WIKI_LINK_RE.finditer(text)}
        pages.append(Page(
            rel_path=rel,
            abs_path=md,
            frontmatter=fm,
            body=body,
            outbound_links=links,
            repo=detect_page_repo(rel),
            scope_repos=detect_manual_scope(rel, fm),
        ))
    return pages


def get_current_repo_root() -> Path | None:
    """Return the working tree root via `git rev-parse`, or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return Path(result.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def get_current_repo_name(repo_root: Path | None) -> str | None:
    """Derive a repo name from `remote.origin.url`; fallback: dir name."""
    if repo_root is None:
        return None
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        url = result.stdout.strip()
        if url:
            m = re.search(r"[/:]([^/:]+?)(?:\.git)?/?$", url)
            if m:
                return m.group(1)
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return repo_root.name


_RENAME_CACHE: dict[str, str] | None = None
_RENAME_CACHE_FAILED = False


def _build_rename_index(repo_root: Path) -> dict[str, str] | None:
    """Map old-path → new-path for every rename in the repo's history.

    Returns None when git can't be invoked or exits non-zero — the caller must
    treat that as "rename detection unavailable" rather than "no renames found",
    because the latter would silently flip `renamed` → `dead` and feed the
    autonomous-delete path with bad data.

    Scanned once per process; subsequent lookups are O(1). The pathspec form
    of `git log` doesn't work for this — git's path filter runs after rename
    detection, so filtering by the old name returns nothing.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--all", "-M", "--diff-filter=R", "--name-status",
             "--pretty=format:"],
            cwd=repo_root, capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    index: dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("R"):
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            old, new = parts[1], parts[2]
            index.setdefault(old, new)
    return index


def check_path_alive(repo_root: Path, path: str) -> tuple[str, str | None]:
    """Return (status, renamed_to).

    status ∈ {alive, dead, renamed, escape, unknown}.
    - `escape`: source resolves outside repo_root (`..` or symlink); never
      autodeleted.
    - `unknown`: rename detection failed; we can't distinguish dead from
      renamed, so the page must not be autodeleted.
    """
    global _RENAME_CACHE, _RENAME_CACHE_FAILED
    try:
        abs_path = (repo_root / path).resolve()
        abs_path.relative_to(repo_root.resolve())
    except ValueError:
        return ("escape", None)
    if abs_path.exists():
        return ("alive", None)
    if _RENAME_CACHE is None and not _RENAME_CACHE_FAILED:
        result = _build_rename_index(repo_root)
        if result is None:
            _RENAME_CACHE_FAILED = True
        else:
            _RENAME_CACHE = result
    if _RENAME_CACHE_FAILED:
        return ("unknown", None)
    new_path = _RENAME_CACHE.get(path) if _RENAME_CACHE else None
    if new_path:
        return ("renamed", new_path)
    return ("dead", None)


def classify_source(src: Any) -> tuple[str, str]:
    """Return (kind, value). kind ∈ {url, wiki, path}."""
    s = str(src).strip()
    if s.startswith(("http://", "https://")):
        return ("url", s)
    if s.startswith("[[") and s.endswith("]]"):
        return ("wiki", s[2:-2].strip())
    return ("path", s)


def check_broken_and_autodelete(
    pages: list[Page],
    current_repo: str | None,
    current_repo_root: Path | None,
) -> tuple[list[dict], list[dict]]:
    broken: list[dict] = []
    autodelete: list[dict] = []

    for page in pages:
        raw_sources = page.frontmatter.get("sources")
        if raw_sources is None:
            continue
        if not isinstance(raw_sources, list):
            broken.append({
                "page": page.rel_path,
                "sources": [{
                    "source": str(raw_sources)[:80],
                    "status": "malformed",
                    "renamed_to": None,
                }],
            })
            continue
        sources = raw_sources
        if not sources:
            continue

        if page.scope_repos is not None:
            owns_page = current_repo in page.scope_repos
        else:
            owns_page = page.repo == current_repo or page.repo is None
        in_scope = current_repo_root is not None and owns_page

        path_results: list[tuple[str, str, str | None]] = []
        has_unverifiable = False  # cross-repo path, url, or wiki source

        for src in sources:
            kind, val = classify_source(src)
            if kind in ("url", "wiki"):
                has_unverifiable = True
                continue
            if not in_scope:
                has_unverifiable = True
                continue
            status, new_path = check_path_alive(current_repo_root, val)
            path_results.append((val, status, new_path))

        non_alive = [r for r in path_results if r[1] != "alive"]
        if non_alive:
            broken.append({
                "page": page.rel_path,
                "sources": [
                    {"source": s, "status": st, "renamed_to": np}
                    for s, st, np in non_alive
                ],
            })

        if (
            path_results
            and not has_unverifiable
            and all(r[1] == "dead" for r in path_results)
        ):
            autodelete.append({
                "page": page.rel_path,
                "protected": protected_bucket(page.rel_path),
                "sources": [
                    {"source": s, "status": st, "renamed_to": np}
                    for s, st, np in path_results
                ],
            })

    return broken, autodelete


def check_aging(pages: list[Page], today: date) -> list[dict]:
    """Flag non-index pages whose last_updated is older than AGING_DAYS."""
    out = []
    for page in pages:
        if page.rel_path == "index.md" or page.rel_path.endswith("/index.md"):
            continue
        lu = page.frontmatter.get("last_updated")
        page_date: date | None = None
        if isinstance(lu, date):
            page_date = lu
        elif lu is not None:
            try:
                y, m, d = (int(x) for x in str(lu).split("-"))
                page_date = date(y, m, d)
            except (ValueError, AttributeError):
                page_date = None
        if page_date is None:
            out.append({
                "page": page.rel_path,
                "last_updated": None,
                "age_days": None,
            })
            continue
        age = (today - page_date).days
        if age > AGING_DAYS:
            out.append({
                "page": page.rel_path,
                "last_updated": page_date.isoformat(),
                "age_days": age,
            })
    return out


def resolve_link(link: str, pages_by_rel: dict[str, Page]) -> str | None:
    """Map a wiki-link target string to an actual KB-relative page path."""
    target = link.strip().strip("/")
    for candidate in (f"{target}.md", f"{target}/index.md"):
        if candidate in pages_by_rel:
            return candidate
    return None


def check_orphans(pages: list[Page]) -> list[str]:
    """Return non-index, non-plan pages with no inbound wiki-link."""
    pages_by_rel = {p.rel_path: p for p in pages}
    inbound: dict[str, set[str]] = {p.rel_path: set() for p in pages}
    for p in pages:
        for link in p.outbound_links:
            target = resolve_link(link, pages_by_rel)
            if target and target != p.rel_path:
                inbound[target].add(p.rel_path)
    orphans = []
    for p in pages:
        if p.rel_path == "index.md" or p.rel_path.endswith("/index.md"):
            continue
        if p.rel_path.startswith("plans/"):
            continue
        if not inbound[p.rel_path]:
            orphans.append(p.rel_path)
    return orphans


def check_concept_gaps(pages: list[Page]) -> list[dict]:
    """Heuristic: spot 'the X table/service/...' with no matching page."""
    pages_by_rel = {p.rel_path: p for p in pages}
    out = []
    for p in pages:
        if p.repo is None:
            continue
        seen = set()
        for m in CONCEPT_RE.finditer(p.body):
            name = m.group(1).lower()
            kind = m.group(2).lower()
            subfolder = TYPE_TO_SUBFOLDER.get(kind)
            if not subfolder:
                continue
            key = (name, kind, subfolder)
            if key in seen:
                continue
            seen.add(key)
            expected = f"wiki/{p.repo}/{subfolder}/{name}.md"
            if expected not in pages_by_rel:
                out.append({
                    "page": p.rel_path,
                    "candidate": f"{name} {kind}",
                    "expected_path": expected,
                })
    return out


def check_needs_source(pages: list[Page]) -> list[str]:
    """Return pages containing a `[needs source]` marker."""
    return [p.rel_path for p in pages if NEEDS_SOURCE_RE.search(p.body)]


def kind_scope(rel_path: str) -> tuple[str, set[str]] | None:
    """Return (scope, valid kinds) for pages that must declare `kind:`."""
    parts = rel_path.split("/")
    if len(parts) >= 3 and parts[0] == "wiki" and parts[2] == "patterns":
        return ("pattern", VALID_PATTERN_KINDS)
    if parts[0] == "manuals" and len(parts) == 2:
        return ("manual", VALID_MANUAL_KINDS)
    return None


def check_kind(pages: list[Page]) -> list[dict]:
    """Flag pages that must declare `kind:` but miss it or use a bad value.

    Two scopes: `patterns/` pages (convention | recipe | template) and
    `manuals/` pages (how-to | explainer). Index pages are skipped.
    """
    out = []
    for p in pages:
        if p.rel_path == "index.md" or p.rel_path.endswith("/index.md"):
            continue
        scope = kind_scope(p.rel_path)
        if scope is None:
            continue
        scope_name, valid = scope
        kind = p.frontmatter.get("kind")
        if kind is None:
            out.append({"page": p.rel_path, "kind": None,
                        "problem": "missing", "scope": scope_name})
        elif str(kind).strip() not in valid:
            out.append({"page": p.rel_path, "kind": str(kind),
                        "problem": "invalid", "scope": scope_name})
    return out


def format_markdown(report: dict) -> str:
    """Render a lint report as a markdown document."""
    lines = []
    lines.append("# KB Lint Report")
    lines.append("")
    lines.append(f"- KB: `{report['kb_path']}`")
    if report["current_repo"]:
        lines.append(f"- Current repo: `{report['current_repo']}`")
    else:
        lines.append("- Current repo: *(not detected — "
                     "source-liveness checks skipped)*")
    lines.append(f"- Date: {report['date']}")
    lines.append(f"- Pages scanned: {report['pages_scanned']}")
    lines.append("")

    s = report["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Broken sources: {s['broken_sources']}")
    lines.append(f"- Aging pages (>{AGING_DAYS}d): {s['aging']}")
    lines.append(f"- Orphan pages: {s['orphans']}")
    lines.append(f"- Concept-gap candidates: {s['concept_gaps']}")
    lines.append(f"- `[needs source]` markers: {s['needs_source']}")
    lines.append(f"- Auto-delete candidates: {s['autodelete']}")
    lines.append("- Protected pages with all sources dead (flag only): "
                 f"{s['protected_dead']}")
    lines.append(f"- `kind:` issues: {s['kind_issues']}")
    lines.append("")

    f = report["findings"]

    lines.append("## 1. Broken sources")
    if not f["broken_sources"]:
        lines.append("*(none)*")
    else:
        for entry in f["broken_sources"]:
            lines.append("")
            lines.append(f"- `{entry['page']}`")
            for s2 in entry["sources"]:
                status = s2["status"]
                if status == "renamed":
                    lines.append(
                        f"  - renamed: `{s2['source']}` → "
                        f"`{s2['renamed_to']}`")
                elif status == "escape":
                    lines.append(
                        f"  - escape: `{s2['source']}` "
                        "(resolves outside repo root)")
                elif status == "unknown":
                    lines.append(
                        f"  - unverifiable: `{s2['source']}` "
                        "(git rename detection failed)")
                elif status == "malformed":
                    lines.append(
                        f"  - malformed: `{s2['source']}` "
                        "(not a YAML list)")
                else:
                    lines.append(f"  - dead: `{s2['source']}`")
    lines.append("")

    lines.append(f"## 2. Aging pages (>{AGING_DAYS} days)")
    if not f["aging"]:
        lines.append("*(none)*")
    else:
        for entry in f["aging"]:
            age = (f"{entry['age_days']}d" if entry["age_days"] is not None
                   else "no date")
            last = entry["last_updated"] or "missing"
            lines.append(
                f"- `{entry['page']}` — {age} (last_updated: {last})")
    lines.append("")

    lines.append("## 3. Orphan pages")
    if not f["orphans"]:
        lines.append("*(none)*")
    else:
        for p in f["orphans"]:
            lines.append(f"- `{p}`")
    lines.append("")

    lines.append("## 4. Concept-gap candidates "
                 "*(regex heuristic; expect false positives)*")
    if not f["concept_gaps"]:
        lines.append("*(none)*")
    else:
        for entry in f["concept_gaps"]:
            lines.append(
                f"- `{entry['page']}` mentions \"{entry['candidate']}\" — "
                f"expected page at `{entry['expected_path']}`")
    lines.append("")

    lines.append("## 5. `[needs source]` markers")
    if not f["needs_source"]:
        lines.append("*(none)*")
    else:
        for p in f["needs_source"]:
            lines.append(f"- `{p}`")
    lines.append("")

    lines.append("## 6. Auto-delete candidates (per Delete protocol)")
    lines.append("")
    lines.append("**Unprotected pages with all in-tree sources dead — "
                 "eligible for autonomous delete:**")
    if not f["autodelete"]:
        lines.append("")
        lines.append("*(none)*")
    else:
        for entry in f["autodelete"]:
            lines.append("")
            lines.append(f"- `{entry['page']}`")
            for s2 in entry["sources"]:
                if s2["status"] == "renamed":
                    lines.append(
                        f"  - renamed: `{s2['source']}` → "
                        f"`{s2['renamed_to']}` "
                        "*(rename detected — consider updating source "
                        "instead)*")
                else:
                    lines.append(f"  - dead: `{s2['source']}`")
    lines.append("")
    lines.append("**Plan and manual pages with all sources dead — "
                 "flag only, never auto-deleted:**")
    if not f["protected_dead"]:
        lines.append("")
        lines.append("*(none)*")
    else:
        for entry in f["protected_dead"]:
            lines.append("")
            lines.append(f"- `{entry['page']}` *({entry['protected']})*")
    lines.append("")

    lines.append("## 7. `kind:` issues")
    if not f["kind_issues"]:
        lines.append("*(none)*")
    else:
        for entry in f["kind_issues"]:
            valid = sorted(VALID_PATTERN_KINDS if entry["scope"] == "pattern"
                           else VALID_MANUAL_KINDS)
            allowed = ", ".join(f"`{v}`" for v in valid)
            if entry["problem"] == "missing":
                lines.append(f"- `{entry['page']}` — missing `kind:` "
                             f"(required on {entry['scope']} pages; "
                             f"one of {allowed})")
            else:
                lines.append(f"- `{entry['page']}` — invalid `kind:` "
                             f"`{entry['kind']}` (must be one of {allowed})")

    return "\n".join(lines)


def main() -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        description="Lint a knowledge base.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "kb_path", type=Path,
        help="Path to the KB root (contains wiki/, plans/, manuals/)")
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON instead of markdown")
    args = parser.parse_args()

    kb_path = args.kb_path.resolve()
    if not kb_path.is_dir():
        print(f"error: kb_path {kb_path} is not a directory", file=sys.stderr)
        return 2
    if not (kb_path / "wiki").is_dir() and not (kb_path / "plans").is_dir():
        print(f"warning: {kb_path} doesn't look like a KB "
              "(no wiki/ or plans/ subdirectory)", file=sys.stderr)

    repo_root = get_current_repo_root()
    repo_name = get_current_repo_name(repo_root)

    pages = walk_kb(kb_path)
    broken, autodelete_all = check_broken_and_autodelete(
        pages, repo_name, repo_root)
    aging = check_aging(pages, date.today())
    orphans = check_orphans(pages)
    concept_gaps = check_concept_gaps(pages)
    needs_source = check_needs_source(pages)
    kind_issues = check_kind(pages)

    autodelete = [a for a in autodelete_all if a["protected"] is None]
    protected_dead = [a for a in autodelete_all if a["protected"]]

    report = {
        "kb_path": str(kb_path),
        "current_repo": repo_name,
        "date": date.today().isoformat(),
        "pages_scanned": len(pages),
        "summary": {
            "broken_sources": len(broken),
            "aging": len(aging),
            "orphans": len(orphans),
            "concept_gaps": len(concept_gaps),
            "needs_source": len(needs_source),
            "autodelete": len(autodelete),
            "protected_dead": len(protected_dead),
            "kind_issues": len(kind_issues),
        },
        "findings": {
            "broken_sources": broken,
            "aging": aging,
            "orphans": orphans,
            "concept_gaps": concept_gaps,
            "needs_source": needs_source,
            "autodelete": autodelete,
            "protected_dead": protected_dead,
            "kind_issues": kind_issues,
        },
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
