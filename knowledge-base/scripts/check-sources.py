#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""
Check `sources:` liveness for one KB page. Used by the Delete protocol to
decide whether a page is safe to auto-delete.

Run from inside a repo's working tree. The script walks up from the page to
find the KB root (a directory containing both `wiki/` and `plans/`), then
resolves the page's repo from its position in the wiki/ tree. Pages under
`plans/` and `manuals/` are protected — they never return `safe-to-delete`.

Run:
    uv run scripts/check-sources.py <page-path>
    uv run scripts/check-sources.py <page-path> --json

Verdicts:
    safe-to-delete   Auto-delete OK per Delete protocol
    partial          Some sources alive, some dead — drop dead, keep page
    all-alive        All sources alive, nothing to do
    flag             Surface to user; reason field explains why
    no-sources       Page has no sources field
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


PROTECTED_BUCKETS = {"plans": "plan", "manuals": "manual"}


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


def classify_source(src: Any) -> tuple[str, str]:
    """Classify a `sources:` entry as (kind, value). Kind: url, wiki, path."""
    s = str(src).strip()
    if s.startswith(("http://", "https://")):
        return ("url", s)
    if s.startswith("[[") and s.endswith("]]"):
        return ("wiki", s[2:-2].strip())
    return ("path", s)


def find_kb_root(start: Path) -> Path | None:
    """Walk up from `start` until a directory with both `wiki/` and `plans/`."""
    current = start.resolve().parent if start.is_file() else start.resolve()
    while current != current.parent:
        if (current / "wiki").is_dir() and (current / "plans").is_dir():
            return current
        current = current.parent
    return None


def get_page_repo(kb_root: Path, page_path: Path) -> str | None:
    """Return the repo name from a page's KB-relative path.

    Pages under wiki/<repo>/... → repo is <repo>.
    Pages under plans/..., manuals/..., or wiki/index.md → None.
    """
    rel = page_path.resolve().relative_to(kb_root).as_posix()
    parts = rel.split("/")
    if len(parts) >= 3 and parts[0] == "wiki":
        return parts[1]
    return None


def protected_bucket(kb_root: Path, page_path: Path) -> str | None:
    """Return 'plan' or 'manual' for pages that are never auto-deleted."""
    rel = page_path.resolve().relative_to(kb_root).as_posix()
    return PROTECTED_BUCKETS.get(rel.split("/")[0])


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


def _build_rename_index(repo_root: Path) -> dict[str, str] | None:
    """Map old-path → new-path for every rename in the repo's history.

    Returns None when git can't be invoked or exits non-zero — the caller must
    treat that as "rename detection unavailable" rather than "no renames found",
    because the latter would silently flip `renamed` → `dead` and feed the
    autonomous-delete path with bad data.

    The pathspec form of `git log` doesn't work: git's path filter runs after
    rename detection, so filtering by the old name returns nothing.
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
            index.setdefault(parts[1], parts[2])
    return index


def check_path_alive(
    repo_root: Path,
    path: str,
    rename_index: dict[str, str] | None,
) -> tuple[str, str | None]:
    """Return (status, renamed_to). Status: alive, dead, renamed, escape, unknown.

    `escape` means the source resolves outside `repo_root` (relative ascent or
    symlink); never autodeleted. `unknown` means rename detection failed and
    the file doesn't currently exist — we can't tell dead from renamed.
    """
    try:
        abs_path = (repo_root / path).resolve()
        abs_path.relative_to(repo_root.resolve())
    except ValueError:
        return ("escape", None)
    if abs_path.exists():
        return ("alive", None)
    if rename_index is None:
        return ("unknown", None)
    new_path = rename_index.get(path)
    if new_path:
        return ("renamed", new_path)
    return ("dead", None)


def determine_verdict(
    page_repo: str | None,
    current_repo: str | None,
    protected: str | None,
    sources: list[dict],
) -> tuple[str, str | None]:
    """Apply the Delete protocol's decision tree to classified sources.

    `protected` is 'plan', 'manual', or None — plans and manuals are never
    auto-deleted, however dead their sources are.
    """
    if not sources:
        return ("no-sources", "page has no sources field")

    if page_repo is not None:
        if current_repo is None:
            return ("flag",
                    f"page belongs to repo '{page_repo}' but no repo "
                    "detected in CWD")
        if page_repo != current_repo:
            return ("flag",
                    f"page belongs to repo '{page_repo}' but CWD is "
                    f"'{current_repo}'")

    path_sources = [s for s in sources if s["kind"] == "path"]
    has_external = any(s["kind"] != "path" for s in sources)

    if not path_sources:
        return ("flag",
                "only external (URL or wiki) sources — can't auto-verify")

    escape = [s for s in path_sources if s["status"] == "escape"]
    if escape:
        return ("flag",
                f"{len(escape)} source path(s) resolve outside the repo root "
                "(`..` or symlink escape) — refusing to verify")

    unknown = [s for s in path_sources if s["status"] == "unknown"]
    if unknown:
        return ("flag",
                f"{len(unknown)} source path(s) can't be verified — git rename "
                "detection unavailable (subprocess failed or non-zero exit)")

    alive = [s for s in path_sources if s["status"] == "alive"]
    dead = [s for s in path_sources if s["status"] == "dead"]
    renamed = [s for s in path_sources if s["status"] == "renamed"]
    not_alive = dead + renamed

    if alive and not_alive:
        return ("partial",
                f"{len(alive)} alive, {len(not_alive)} not-alive — "
                "drop dead/update renamed, keep page")
    if alive:
        return ("all-alive", None)
    if renamed:
        return ("flag",
                f"all in-tree paths gone but {len(renamed)} have rename "
                "targets — update sources, don't delete")
    if has_external:
        return ("flag",
                "all in-tree paths dead but external (URL/wiki) sources "
                "present — can't fully verify")
    if protected:
        return ("flag",
                f"all in-tree paths dead but page is a {protected} "
                f"({protected}s are never auto-deleted)")
    return ("safe-to-delete",
            "all in-tree sources dead (no renames detected), "
            "no externals, not a plan or manual")


def assess(page_path: Path) -> dict:
    """Build the full assessment dict for a wiki page."""
    text = page_path.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)
    raw_sources = fm.get("sources", [])
    if not isinstance(raw_sources, list):
        raw_sources = []

    kb_root = find_kb_root(page_path)
    page_repo = get_page_repo(kb_root, page_path) if kb_root else None
    protected = protected_bucket(kb_root, page_path) if kb_root else None

    repo_root = get_current_repo_root()
    current_repo = get_current_repo_name(repo_root)
    rename_index = _build_rename_index(repo_root) if repo_root else {}

    sources: list[dict] = []
    for src in raw_sources:
        kind, val = classify_source(src)
        if kind == "url":
            sources.append(
                {"source": val, "kind": "url", "status": "external"})
        elif kind == "wiki":
            sources.append(
                {"source": val, "kind": "wiki", "status": "external"})
        else:
            cross_repo = (page_repo is not None
                          and page_repo != current_repo)
            if repo_root is None or cross_repo:
                sources.append(
                    {"source": val, "kind": "path", "status": "not-checked"})
            else:
                status, renamed_to = check_path_alive(
                    repo_root, val, rename_index)
                entry: dict = {"source": val, "kind": "path", "status": status}
                if renamed_to:
                    entry["renamed_to"] = renamed_to
                sources.append(entry)

    verdict, reason = determine_verdict(
        page_repo, current_repo, protected, sources)

    return {
        "page": str(page_path),
        "kb_root": str(kb_root) if kb_root else None,
        "page_repo": page_repo,
        "current_repo": current_repo,
        "is_plan": protected == "plan",
        "is_manual": protected == "manual",
        "verdict": verdict,
        "reason": reason,
        "sources": sources,
    }


def format_human(result: dict) -> str:
    """Render an assess() result as a human-readable text block."""
    lines = []
    lines.append(f"Page: {result['page']}")
    if result["page_repo"]:
        lines.append(f"Page repo: {result['page_repo']}")
    if result["current_repo"]:
        lines.append(f"Current repo: {result['current_repo']}")
    if result["is_plan"]:
        lines.append("Protected: plan (never auto-deleted)")
    elif result["is_manual"]:
        lines.append("Protected: manual (never auto-deleted)")
    else:
        lines.append("Protected: no")
    lines.append(f"Verdict: {result['verdict']}")
    if result["reason"]:
        lines.append(f"Reason: {result['reason']}")
    lines.append("")
    lines.append("Sources:")
    if not result["sources"]:
        lines.append("  (none)")
    else:
        marker = {
            "alive": "[OK]      ",
            "dead": "[DEAD]    ",
            "renamed": "[RENAMED] ",
            "external": "[EXTERNAL]",
            "not-checked": "[SKIP]    ",
            "escape": "[ESCAPE]  ",
            "unknown": "[UNKNOWN] ",
        }
        for s in result["sources"]:
            line = f"  {marker.get(s['status'], '[?]')} {s['source']}"
            if s.get("renamed_to"):
                line += f"  →  {s['renamed_to']}"
            lines.append(line)
    return "\n".join(lines)


def main() -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        description="Check sources liveness for a wiki page.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "page", type=Path, help="Path to the wiki page (.md file)")
    parser.add_argument(
        "--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    page_path = args.page.resolve()
    if not page_path.is_file():
        print(f"error: {page_path} is not a file", file=sys.stderr)
        return 2

    result = assess(page_path)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_human(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
