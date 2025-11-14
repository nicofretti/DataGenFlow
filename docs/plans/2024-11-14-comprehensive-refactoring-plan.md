---
title: Comprehensive Refactoring Plan
description: Systematic cleanup of codebase, documentation, and structure
date: 2024-11-14
---

# Comprehensive Refactoring Plan

## Overview

This document outlines a systematic refactoring of the DataGenFlow codebase to address:
- Outdated and misaligned documentation
- Code violations of established guidelines
- Inconsistent llm/ folder structure and naming
- Dead code from abandoned features (website)
- Missing tests for critical functionality

**Approach:** Parallel Streams (Modular) - Refactor by module with incremental progress.

**Timeline:** 5-6 days of systematic work.

## Goals

1. **Clean codebase** - All code follows rules-backend.md and rules-frontend.md
2. **Updated documentation** - Style compliant, content accurate
3. **Clear structure** - Consistent llm/ naming, updated references
4. **No dead code** - Remove abandoned features and unused code
5. **Essential tests** - Add tests where they prevent regressions
6. **Enhanced guides** - Document anti-patterns discovered during refactoring

## File Structure Changes

### llm/ Folder Restructuring

**Current structure (inconsistent):**
```
llm/
  backend_code_guide.md
  frontend_code_guide.md
  agent_code_guide.md
  backend_technical_guide.md
  frontend_technical_guide.md
  project_technical_guide.md
```

**New structure (consistent naming):**
```
llm/
  rules-backend.md       # Coding standards for backend
  rules-frontend.md      # Coding standards for frontend
  rules-agent.md         # Agent behavior guidelines
  state-backend.md       # Backend architecture/implementation status
  state-frontend.md      # Frontend architecture/implementation status
  state-project.md       # Overall project status
```

**Naming convention:**
- `rules-*.md`: Prescriptive guides (how to write code)
- `state-*.md`: Descriptive references (current implementation)

### Files to Update

**`.claude/CLAUDE.md`:**
```markdown
## Internal Files
- llm/state-project.md: project status, never commit, update gradually
- llm/state-backend.md: backend architecture, never commit, update gradually
- llm/state-frontend.md: frontend architecture, never commit, update gradually
- llm/rules-backend.md: backend coding standards (follow for backend tasks)
- llm/rules-frontend.md: frontend coding standards (follow for frontend tasks)
- llm/rules-agent.md: agent behavior guidelines
```

**`.github/instructions/*.instructions.md`:**
Update all references:
- Line 194: `llm/backend_technical_guide.md` → `llm/state-backend.md`
- Line 195: `llm/frontend_technical_guide.md` → `llm/state-frontend.md`
- Line 196: `llm/project_technical_guide.md` → `llm/state-project.md`
- Line 309-325: Update all examples to use new naming

Add naming convention clarification after line 189:
```markdown
**naming convention:**
- `llm/state-*.md`: current implementation status
- `llm/rules-*.md`: coding standards and guidelines
```

## Execution Plan

### Phase 0: Dead Code Discovery & Removal (Day 1)

**Automated searches:**
```bash
# Find TODO/FIXME/WIP/DEPRECATED comments
grep -rn "TODO\|FIXME\|WIP\|DEPRECATED\|XXX\|HACK" \
  --include="*.py" --include="*.tsx" --include="*.ts" \
  --exclude-dir=node_modules --exclude-dir=.venv \
  lib/ frontend/src/ app.py > dead_code_todos.txt

# Find commented-out code blocks
grep -rn "^[[:space:]]*#.*def \|^[[:space:]]*#.*class \|^[[:space:]]*//.*function" \
  --include="*.py" --include="*.tsx" --include="*.ts" \
  --exclude-dir=node_modules --exclude-dir=.venv \
  lib/ frontend/src/ app.py > commented_code.txt

# Search for "website" references
grep -rni "website" \
  --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git \
  . > website_references.txt

# Find empty or near-empty files
find lib/ frontend/src/ -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) \
  -size -100c > small_files.txt

# Find feature flags or experimental code
grep -rni "feature_flag\|experimental\|beta\|alpha" \
  --include="*.py" --include="*.tsx" --include="*.ts" \
  lib/ frontend/src/ app.py > experimental_code.txt
```

**Manual inspection:**
- [ ] Review search results
- [ ] Check Makefile for unused targets
- [ ] Check .github/workflows/ for unused jobs
- [ ] Check package.json for unused scripts/dependencies
- [ ] Check pyproject.toml for unused dependencies
- [ ] Check .env.example for vars from removed features
- [ ] Review website/ directory (confirmed dead)
- [ ] Check lib/blocks/custom/ for abandoned blocks
- [ ] Check docs/ for outdated guides

**Confirmed removals:**
- website/ directory and all references
- .github/workflows/deploy_website.yml
- Makefile website-related targets
- Documentation about website deployment

**Deliverables:**
- DEAD_CODE_REPORT.md (document what was removed and why)
- Clean codebase with dead code removed
- Commit: "clean: remove abandoned features and dead code"

### Phase 1: Foundation Setup (Day 1)

**1.1 Restructure llm/ folder:**
```bash
cd llm/
mv backend_code_guide.md rules-backend.md
mv frontend_code_guide.md rules-frontend.md
mv agent_code_guide.md rules-agent.md
mv backend_technical_guide.md state-backend.md
mv frontend_technical_guide.md state-frontend.md
mv project_technical_guide.md state-project.md
```

**1.2 Update references:**
- Edit `.claude/CLAUDE.md`
- Edit `.github/instructions/*.instructions.md`

**1.3 Create tracking files:**
- `docs/AUDIT_REPORT.md` (temporary, track doc violations)
- `REFACTORING_NOTES.md` (track patterns, improvements, decisions)

**1.4 Baseline tests:**
```bash
# Run all tests, record current state
pytest tests/ -v > test_baseline.txt
cd frontend && npm test > ../frontend_test_baseline.txt
```

**Deliverables:**
- Renamed llm/ files with clear convention
- Updated references in all config files
- Tracking infrastructure set up
- Commit: "refactor: reorganize llm/ folder with clear naming"

### Phase 2: Documentation Audit & Fix (Day 1-2)

**2.1 Documentation audit:**

Files to audit (12 total):
- docs/overview.md
- docs/how_to_use.md
- docs/how_to_create_blocks.md
- docs/templates.md
- docs/template_text_classification.md
- docs/template_qa_generation.md
- docs/template_json_extraction.md
- docs/markdown_style_guide.md
- docs/plans/*.md (3 plan files)
- README.md

**Style checks (from markdown_style_guide.md):**
- [ ] Has YAML frontmatter (except README.md)
- [ ] No H1 in content
- [ ] Table of contents present (except README.md)
- [ ] All code blocks have language specified
- [ ] All code blocks properly closed
- [ ] Anchor links use correct format
- [ ] Admonitions use proper format (`> **Note:**`)
- [ ] Internal links omit `.md` extension
- [ ] Headings follow logical hierarchy

**Content accuracy checks (against llm/state-*.md):**
- [ ] API endpoints match current implementation
- [ ] Block descriptions match actual code
- [ ] UI flow matches current frontend
- [ ] Configuration examples are accurate
- [ ] Architecture diagrams reflect reality
- [ ] Code examples actually work

**2.2 Fix documentation:**
- Fix style violations first (quick wins)
- Fix content inaccuracies (reference actual code)
- Commit per file or logical group
- Update AUDIT_REPORT.md as you go

**Deliverables:**
- All documentation style-compliant
- All documentation content-accurate
- Completed AUDIT_REPORT.md
- Commits: "docs: fix markdown style in [file]", "docs: update [file] to match implementation"

### Phase 3: Modular Code Refactoring (Day 2-5)

**Per-module workflow:**

For each module:
1. **Audit** - Read all files, check against rules
2. **Fix violations** - Critical first (security, silent failures), then style
3. **Harmonize patterns** - Standardize to dominant codebase patterns
4. **Add essential tests** - Only if fixing bugs or complex logic
5. **Run tests** - Ensure all passing
6. **Update state docs** - Document any architectural changes
7. **Document anti-patterns** - Add new patterns to rules files
8. **Review** - Use review agent to validate
9. **Commit** - Logical grouped changes

#### Module 1: Block System (lib/blocks/)

**Files:**
- lib/blocks/base.py
- lib/blocks/config.py
- lib/blocks/registry.py
- lib/blocks/builtin/*.py
- lib/blocks/custom/*.py

**Audit against:** llm/rules-backend.md

**Common issues to check:**
- [ ] Functions >30 lines (god functions)
- [ ] Functions >3 params without dataclass
- [ ] Silent failures (empty except blocks)
- [ ] Missing logger.exception() in error handlers
- [ ] SQL injection vulnerabilities
- [ ] Missing type hints
- [ ] Inconsistent error handling patterns

**Harmonization opportunities:**
- Error handling style across all blocks
- Validation patterns
- Logging format

**Deliverables:**
- Clean block system code
- Updated llm/state-backend.md
- New anti-patterns documented in llm/rules-backend.md
- Commit: "refactor: clean up block system"

#### Module 2: Core Engine (lib/workflow.py, storage.py, job_*.py)

**Files:**
- lib/workflow.py
- lib/storage.py
- lib/job_queue.py
- lib/job_processor.py
- lib/generator.py
- lib/template_renderer.py
- lib/errors.py

**Audit against:** llm/rules-backend.md

**Focus areas:**
- Database transaction handling
- Async/await patterns
- Error propagation
- Resource cleanup

**Deliverables:**
- Clean core engine code
- Updated llm/state-backend.md
- Commit: "refactor: clean up core engine"

#### Module 3: API Layer (app.py, config.py)

**Files:**
- app.py
- config.py

**Audit against:** llm/rules-backend.md

**Focus areas:**
- Input validation (Pydantic models)
- Error response consistency
- Dependency injection
- Security (size limits, parameterized queries)

**Deliverables:**
- Clean API layer
- Updated llm/state-backend.md
- Commit: "refactor: clean up API layer"

#### Module 4: Frontend Pages (frontend/src/pages/)

**Files:**
- frontend/src/pages/Pipelines.tsx
- frontend/src/pages/Generator.tsx
- frontend/src/pages/Review.tsx

**Audit against:** llm/rules-frontend.md

**Common issues:**
- [ ] Bloated components (too many hooks)
- [ ] Silent error handling
- [ ] Prop drilling (>5 props)
- [ ] Direct fetch calls (should use service layer)
- [ ] Missing useCallback/useMemo
- [ ] Missing cleanup in useEffect
- [ ] `any` types or `as` assertions
- [ ] Direct localStorage access

**Harmonization opportunities:**
- API call patterns (service layer vs inline)
- Error display (toast vs modal vs inline)
- State management approach

**Deliverables:**
- Clean frontend pages
- Updated llm/state-frontend.md
- Commit: "refactor: clean up frontend pages"

#### Module 5: Frontend Components (frontend/src/components/)

**Files:**
- All components in frontend/src/components/

**Audit against:** llm/rules-frontend.md

**Focus areas:**
- Component size and responsibility
- Reusable patterns
- Error boundaries
- TypeScript types

**Deliverables:**
- Clean frontend components
- Updated llm/state-frontend.md
- Commit: "refactor: clean up frontend components"

### Phase 4: Final Validation (Day 5-6)

**4.1 Run full test suite:**
```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Compare to baseline
diff test_baseline.txt current_tests.txt
```

**4.2 Review llm/ files:**
- [ ] All state-*.md files reflect current implementation
- [ ] All rules-*.md files include new anti-patterns discovered
- [ ] No references to old file names
- [ ] All architectural changes documented

**4.3 Run review agent:**
- Use `.github/instructions/*.instructions.md`
- Review entire codebase
- Address any findings

**4.4 Finalize documentation:**
- Complete REFACTORING_NOTES.md with summary
- Document key improvements and decisions
- List anti-patterns discovered and added
- Note test coverage improvements

**4.5 Cleanup:**
- Remove temporary files (AUDIT_REPORT.md, search results)
- Remove test baselines
- Final review of git status

**4.6 Final commit:**
```bash
git add .
git commit -m "refactor: complete systematic cleanup

- Reorganized llm/ folder with clear naming convention
- Fixed all documentation style and content issues
- Removed dead code (website feature)
- Refactored all modules against coding guidelines
- Harmonized patterns across codebase
- Added essential tests for bug fixes
- Documented new anti-patterns in guides"
```

**Deliverables:**
- Fully validated codebase
- Complete REFACTORING_NOTES.md
- All tests passing
- Clean git history

## Anti-Pattern Discovery Process

**When you find a repeated violation or particularly problematic pattern:**

### Add to appropriate rules file

**llm/rules-backend.md or llm/rules-frontend.md:**
```markdown
### anti-patterns to reject (add new entry)
- [ ] [PATTERN NAME] - description
  ```[language]
  # bad (found in: file1.py:123, file2.py:456)
  [wrong code example]

  # good
  [correct code example]
  ```
  why: explanation of why it's problematic
  found during refactoring: [list of locations]
```

### Add to review checklist

**.github/instructions/*.instructions.md:**
Add to appropriate checklist section (backend or frontend anti-patterns).

### Document in REFACTORING_NOTES.md

```markdown
## Anti-Patterns Discovered

### Backend:
1. Nested try-except without context (found in 3 files)
   - Added to rules-backend.md line 67
   - Added to review checklist line 89

### Frontend:
1. Polling without cleanup (found in 2 files)
   - Added to rules-frontend.md line 123
   - Added to review checklist line 145
```

## Pattern Harmonization Guidelines

**When you find inconsistent patterns across the codebase:**

### Decision Tree

```
Found inconsistency?
├─ Does it violate a rule?
│  └─ YES → Fix (mandatory)
│  └─ NO → Continue
│
├─ Is there a dominant pattern (used 3+ times)?
│  └─ YES → Harmonize to dominant pattern
│  └─ NO → Continue
│
├─ Is it confusing or unclear?
│  └─ YES → Improve for clarity
│  └─ NO → Leave as-is (don't over-engineer)
```

### Document Harmonization

**In REFACTORING_NOTES.md:**
```markdown
## Pattern Harmonization - Module [X]

### [Pattern Name] standardized
Before: Mixed approaches
- file1: approach A
- file2: approach B
- file3: approach C

After: Consistent pattern
- All files: approach A

Rationale: Matches 80% of existing codebase, aligns with rules
```

**In llm/state-*.md:**
Document the chosen pattern with rationale.

## Essential Testing Guidelines

**Add tests ONLY when:**
- [ ] Fixed a bug (prevent regression)
- [ ] Complex validation logic with edge cases
- [ ] Critical data transformations

**Don't add tests for:**
- [ ] Simple getters/setters
- [ ] Trivial pass-through functions
- [ ] Code already covered by integration tests

**Track in REFACTORING_NOTES.md:**
```markdown
## Tests Added (if any)

### Module 1: Block System
- test_validator_edge_case.py - fixed bug with empty input, added test

### Module 2: Core Engine
- test_storage_concurrent_writes.py - found race condition, added minimal test
```

## Key Principles

Throughout the refactoring:

1. **Systematic approach** - Module by module, phase by phase
2. **Test after changes** - Run tests after each module
3. **Document as you go** - Update state files, track patterns
4. **Learn from patterns** - Add anti-patterns to guides
5. **Harmonize to dominant patterns** - Don't invent new patterns
6. **Commit logical groups** - Small, focused commits
7. **Essential tests only** - No test theater
8. **Keep it simple** - Improvements, not rewrites

## Success Criteria

Refactoring is complete when:

- [x] llm/ folder has clear naming convention
- [x] All references updated (.claude/CLAUDE.md, review instructions)
- [x] All documentation follows markdown_style_guide.md
- [x] All documentation content matches current implementation
- [x] Dead code removed (website, abandoned features)
- [x] All modules comply with rules-backend.md / rules-frontend.md
- [x] Patterns harmonized across codebase
- [x] Anti-patterns discovered and documented in guides
- [x] Essential tests added for bug fixes
- [x] All tests passing
- [x] Review agent approves all modules
- [x] REFACTORING_NOTES.md documents improvements

## Notes

- This is an improvement pass, not a rewrite
- Follow the principle: "Make it slightly better than you found it"
- Don't introduce new abstractions or patterns
- Harmonize to what exists and works well
- Document learnings for future development
