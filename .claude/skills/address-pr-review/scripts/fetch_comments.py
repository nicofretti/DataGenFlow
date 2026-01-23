#!/usr/bin/env python3
"""
Fetch PR review comments with full body content.

Usage:
    python fetch_comments.py <PR_NUMBER>              # unresolved only
    python fetch_comments.py <PR_NUMBER> --all        # all comments
    python fetch_comments.py <PR_NUMBER> --id <ID>    # single comment
    python fetch_comments.py <PR_NUMBER> --summary    # counts only
"""

import json
import re
import subprocess
import sys
from typing import Any

RESOLVED_MARKERS = ["Addressed in commit", "Resolved in", "✅ Addressed"]
SEVERITY_PATTERN = re.compile(r"_([⚠️🛠️]+\s*[^_]+)_\s*\|\s*_([🟠🟡🔴]+\s*\w+)_")
TITLE_PATTERN = re.compile(r"\*\*([^*]+)\*\*")


def get_repo() -> str:
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "owner,name", "-q", '.owner.login + "/" + .name'],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(1)
    return result.stdout.strip()


def fetch_comments(pr_number: str) -> list[dict[str, Any]]:
    repo = get_repo()
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}/comments", "--paginate", "--slurp"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"failed to fetch comments: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    # --slurp wraps paginated results in an outer array
    pages = json.loads(result.stdout)
    return [comment for page in pages for comment in page]


def is_resolved(comment: dict[str, Any]) -> bool:
    body = comment.get("body", "")
    return any(marker in body for marker in RESOLVED_MARKERS)


def parse_comment(comment: dict[str, Any]) -> dict[str, Any]:
    """Extract essential info from comment body."""
    body = comment.get("body", "")

    # extract severity
    severity_match = SEVERITY_PATTERN.search(body)
    severity = severity_match.group(2).strip() if severity_match else ""

    # extract title (first bold text)
    title_match = TITLE_PATTERN.search(body)
    title = title_match.group(1).strip() if title_match else ""

    # extract suggested fix (content between ```diff and ```)
    diff_match = re.search(r"```diff\n(.*?)```", body, re.DOTALL)
    suggested_fix = diff_match.group(1).strip() if diff_match else ""

    # extract description (text after title, before <details>)
    desc = ""
    if title_match:
        after_title = body[title_match.end() :]
        details_pos = after_title.find("<details>")
        if details_pos >= 0:
            desc = after_title[:details_pos].strip()
        else:
            desc = after_title.strip()
    else:
        # no bold title - use full body as description
        desc = body.strip()
    if len(desc) > 500:
        desc = desc[:500].rstrip() + "…"

    # clean description of markdown artifacts
    desc = re.sub(r"<!--.*?-->", "", desc, flags=re.DOTALL).strip()
    desc = re.sub(r"\n{3,}", "\n\n", desc)

    return {
        "id": comment["id"],
        "file": comment["path"],
        "line": comment.get("line"),
        "severity": severity,
        "title": title,
        "description": desc,
        "suggested_fix": suggested_fix,
        "resolved": is_resolved(comment),
    }


def print_comment(
    parsed: dict[str, Any], index: int | None = None, total: int | None = None
) -> None:
    prefix = f"[{index}/{total}] " if index and total else ""
    loc = f"{parsed['file']}:{parsed['line']}" if parsed["line"] else parsed["file"]

    print(f"\n{'=' * 60}")
    print(f"{prefix}ID: {parsed['id']}")
    print(f"Location: {loc}")
    if parsed["severity"]:
        print(f"Severity: {parsed['severity']}")
    if parsed["title"]:
        print(f"Issue: {parsed['title']}")
    if parsed["description"]:
        print(f"\n{parsed['description']}")
    if parsed["suggested_fix"]:
        print(f"\nFix:\n```diff\n{parsed['suggested_fix']}\n```")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pr_number = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--unresolved"

    if not pr_number.isdigit():
        print("PR number must be numeric")
        sys.exit(1)
    if mode == "--id" and len(sys.argv) <= 3:
        print("missing id for --id")
        sys.exit(1)

    comments = fetch_comments(pr_number)
    top_level = [c for c in comments if c.get("in_reply_to_id") is None]

    if mode == "--id" and len(sys.argv) > 3:
        target_id = int(sys.argv[3])
        for c in top_level:
            if c["id"] == target_id:
                print_comment(parse_comment(c))
                sys.exit(0)
        print(f"comment {target_id} not found")
        sys.exit(1)

    if mode == "--summary":
        unresolved = [c for c in top_level if not is_resolved(c)]
        resolved = len(top_level) - len(unresolved)
        print(f"total: {len(top_level)}, resolved: {resolved}, unresolved: {len(unresolved)}")
        if unresolved:
            print("\nunresolved:")
            for c in unresolved:
                p = parse_comment(c)
                loc = f"{p['file']}:{p['line']}" if p["line"] else p["file"]
                sev = f" [{p['severity']}]" if p["severity"] else ""
                title = f" - {p['title']}" if p["title"] else ""
                print(f"  {p['id']}: {loc}{sev}{title}")
        sys.exit(0)

    if mode == "--unresolved" or mode not in ["--all", "--id", "--summary"]:
        top_level = [c for c in top_level if not is_resolved(c)]
        print(f"showing {len(top_level)} unresolved comments")
    else:
        print(f"showing {len(top_level)} comments")

    if not top_level:
        print("no comments.")
        sys.exit(0)

    for i, c in enumerate(top_level, 1):
        print_comment(parse_comment(c), i, len(top_level))
