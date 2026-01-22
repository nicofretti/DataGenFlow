---
name: address-pr-review
description: Use when you have PR review comments to address and want to evaluate each comment's validity before deciding to fix, reply, or skip
---

# Address PR Review Comments

## Overview

Interactive workflow: analyze PR review comment validity, recommend action, let user decide (fix/reply/skip).

## When to Use

- PR has review comments needing evaluation before action
- Reviewer feedback might be incorrect or needs discussion
- Comments require varied responses (fix/reply/skip)
- Need to balance code quality with respectful reviewer engagement

## When NOT to Use

- All comments are clearly valid and straightforward to fix
- No comments yet or doing pre-review self-review
- Comments only on non-code files without technical analysis needed

## Workflow Overview

```dot
digraph pr_review_flow {
    "Fetch PR comments" [shape=box];
    "More comments?" [shape=diamond];
    "Show comment + file context" [shape=box];
    "Analyze validity" [shape=box];
    "Recommend action" [shape=box];
    "Ask user: Fix/Reply/Skip/Quit?" [shape=diamond];
    "Make code changes" [shape=box];
    "Draft reply" [shape=box];
    "Track as skipped" [shape=box];
    "Show summary" [shape=box];

    "Fetch PR comments" -> "More comments?";
    "More comments?" -> "Show comment + file context" [label="yes"];
    "More comments?" -> "Show summary" [label="no"];
    "Show comment + file context" -> "Analyze validity";
    "Analyze validity" -> "Recommend action";
    "Recommend action" -> "Ask user: Fix/Reply/Skip/Quit?";
    "Ask user: Fix/Reply/Skip/Quit?" -> "Make code changes" [label="Fix"];
    "Ask user: Fix/Reply/Skip/Quit?" -> "Draft reply" [label="Reply"];
    "Ask user: Fix/Reply/Skip/Quit?" -> "Track as skipped" [label="Skip"];
    "Ask user: Fix/Reply/Skip/Quit?" -> "Show summary" [label="Quit"];
    "Make code changes" -> "More comments?";
    "Draft reply" -> "More comments?";
    "Track as skipped" -> "More comments?";
}
```

## Fetching Comments

**CRITICAL**: Do NOT use `gh api --jq` directly - it truncates comment bodies.

Use the included script:

```bash
# summary with counts and titles
python .claude/skills/address-pr-review/scripts/fetch_comments.py <PR> --summary

# show unresolved comments (default)
python .claude/skills/address-pr-review/scripts/fetch_comments.py <PR>

# single comment by ID
python .claude/skills/address-pr-review/scripts/fetch_comments.py <PR> --id <ID>

# all comments including resolved
python .claude/skills/address-pr-review/scripts/fetch_comments.py <PR> --all
```

## Quick Reference

**Critical principle:** Reviewer may be wrong - analyze validity before recommending action.

| Phase | Actions |
|-------|---------|
| **Fetch** | Run `--summary` first to see counts<br>Then `--id <ID>` for each comment to analyze<br>Exit if no unresolved comments |
| **Per Comment** | Show: file:line, author, comment, ±10 lines context<br>Analyze: Valid/Nitpick/Disagree/Question<br>Recommend: Fix/Reply/Skip with reasoning |
| **Fix** | Minimal changes per llm/rules-*.md<br>Offer reply draft: `Fixed: [what]. [why]`<br>Show: `gh api --method POST repos/{owner}/{repo}/pulls/comments/$ID/replies -f body="..."` |
| **Reply** | Draft based on type: Question/Suggestion/Disagreement<br>Let user edit<br>Show gh command (never auto-post) |
| **Summary** | Processed X/N: Fixed Y, Replied Z, Skipped W<br>List: files modified, reply drafts, next steps |

## Critical Principles

| Principle | Violation Pattern |
|-----------|-------------------|
| **Analyze first** | Accepting all feedback as valid without critical analysis |
| **Never auto-post** | Posting replies automatically instead of showing gh command |
| **One at a time** | Batch processing all comments without individual analysis |
| **Show context** | Making changes without displaying ±10 lines around code |
| **Minimal changes** | Large refactors in response to small comments |
| **Follow standards** | Ignoring llm/rules-*.md when fixing |
| **Respectful honesty** | Being defensive/dismissive when reviewer is wrong |
| **User control** | Posting drafts without letting user edit first |

## Reply Formats

- Fix: `Fixed: [what]. [why]`
- Update: `Updated: [what]`
- Answer: `[explanation]`
- Acknowledge: `Good catch, [action/reason]`
- Disagree: `[respectful reasoning]`

## Setup & Usage

Requires: `gh` CLI authenticated, GitHub remote configured

```bash
# Start session
"use address-pr-review for PR <number>"

# Or list PRs first
"use address-pr-review"
```
