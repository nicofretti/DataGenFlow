---
name: code-review
description: Use after completing implementation to review code quality, user impact, test coverage, and documentation before creating a PR
---

# Code Review

## Overview

Review code for quality, user impact, tests, and documentation. Balance technical excellence with practical simplicity.

**Core principle:** Clean code should serve users, not just developers.

## When to Use

- After completing a feature or bug fix
- Before creating a pull request
- When reviewing changes before merge

## When NOT to Use

- Trivial changes (typo fixes)
- Documentation-only changes
- Initial exploration/prototyping

## Review Process

| Phase | Focus | Key Question |
|-------|-------|--------------|
| 1. Identify | What changed? | `git diff --name-only develop` |
| 2. User Impact | How does this affect users? | Is UX better or worse? |
| 3. Code Quality | Does it follow standards? | KISS + no anti-patterns? |
| 4. Tests | Is it covered? | New code = new tests? |
| 5. Docs | What needs updating? | llm/state-*.md current? |

---

## Phase 1: Identify Changes

Categorize changed files:
- **Backend:** `lib/`, `app.py`
- **Frontend:** `frontend/src/`
- **Tests:** `tests/`
- **Docs:** `llm/`, `*.md`

Note change type: new feature | bug fix | refactoring | enhancement

---

## Phase 2: User Impact

**Ask for each change:**
1. Does this affect what users see or do?
2. Are error messages user-friendly (not technical jargon)?
3. Are loading states shown?
4. Can users recover from errors?
5. Is this the simplest UX possible?

**Red flags:**
- Silent failures (user doesn't know something failed)
- Lost work on errors
- Unclear feedback ("Error: 500" vs "Could not save")
- Unnecessary complexity exposed to users

---

## Phase 3: Code Quality

### KISS Check

Can each function be explained in one sentence? If not, it's too complex.

### Backend Anti-patterns (blocking)

- [ ] Silent failures (empty except blocks)
- [ ] God functions (>30 lines, >3 params)
- [ ] SQL injection (f-strings in queries)
- [ ] Missing error context
- [ ] Walrus operators / complex one-liners

### Frontend Anti-patterns (blocking)

- [ ] Empty catch blocks
- [ ] Inline fetch (not in service layer)
- [ ] Missing useEffect cleanup
- [ ] `any` types or `as` assertions
- [ ] Hardcoded colors (use theme: fg.*, canvas.*)
- [ ] Prop drilling (>5 props)

### Security

- [ ] Inputs validated at API boundary
- [ ] SQL parameterized (`?` placeholders)
- [ ] No secrets in code/logs

---

## Phase 4: Test Coverage

| Change Type | Required Test |
|-------------|---------------|
| New API endpoint | Unit test |
| New block | `tests/blocks/test_*.py` |
| Bug fix | Regression test |
| User workflow change | E2E test |
| Refactoring | Existing tests pass |

**Test quality:**
- Naming: `test_<method>_<scenario>_<expected>`
- One behavior per test
- Error cases tested, not just happy path

---

## Phase 5: Documentation

**Update llm/state-*.md when:**
- New API endpoint → `state-backend.md`
- New block → `state-backend.md`
- New component/page → `state-frontend.md`
- Architecture change → `state-project.md`

**Code comments:** explain WHY, not what. Lowercase, concise.

---

## Output Format

```markdown
### User Impact
[UX improvements or issues found]

### Anti-patterns
[location + violation + fix, or "none"]

### Code Quality Issues
[severity + location + fix, or "none"]

### Test Coverage
[required: present/missing | gaps if any]

### Documentation Updates
[files needing update, or "none"]

### Verdict
[BLOCK | REQUEST CHANGES | APPROVE]
Reason: [brief explanation]
```

---

## Verdict Rules

| Condition | Verdict |
|-----------|---------|
| Anti-patterns found | BLOCK |
| Security issues | BLOCK |
| Missing required tests | REQUEST CHANGES |
| Needs doc updates | REQUEST CHANGES |
| All checks pass | APPROVE |

---

## Golden Rules

1. Anti-patterns are blocking - always reject
2. User experience matters - clean code that hurts UX is bad code
3. KISS wins - one sentence explanation or it's too complex
4. Tests are not optional - new code needs tests
5. Fail loudly - silent failures are never acceptable
