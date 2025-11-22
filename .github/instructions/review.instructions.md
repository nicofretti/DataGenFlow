# code review - datagenflow

review code for quality, security, and consistency. flag anti-patterns, verify documentation updates, ensure tests exist.

---

## how to use

1. scan for blocking issues - anti-patterns, security flaws, silent failures
2. check code quality - follows llm/rules-backend.md or llm/rules-frontend.md
3. verify documentation - identify which llm/state-*.md files need updates
4. validate tests - new code has tests, error cases covered
5. provide verdict - block, request changes, or approve

this file is self-contained. all rules needed for review are below. do not read external files.

---

## project context

- type: full-stack data generation platform (fastapi + react + typescript)
- philosophy: simplicity over cleverness, clarity over abstraction
- style: minimal functions, explicit dependencies, fail fast and loud

llm file structure:
- `llm/rules-backend.md` - backend coding standards
- `llm/rules-frontend.md` - frontend coding standards
- `llm/rules-agent.md` - agent behavior guidelines
- `llm/state-backend.md` - backend implementation status
- `llm/state-frontend.md` - frontend implementation status
- `llm/state-project.md` - overall project status

golden rule: if code cannot be explained in one sentence, it's too complex.

---

## review priorities

priority 1: blocking issues (must fix)
- anti-patterns from checklists below
- security vulnerabilities (sql injection, xss, missing validation)
- silent failures (empty catch/except blocks)
- broken tests
- missing tests for: new api endpoints, new blocks, bug fixes
- hardcoded colors in UI (#000, #fff, rgb() instead of theme variables)

priority 2: code quality (should fix)
- violations of llm/rules-*.md guidelines
- missing error handling
- missing type hints
- functions >30 lines, >3 params
- classes >7 public methods

priority 3: documentation (should update)
- llm/state-*.md files need updates when architecture changes
- code comments missing for complex logic
- comments explain what instead of why

priority 4: improvements (nice to have)
- extract duplicate code
- add memoization where helpful
- improve naming clarity

---

## backend checklist

### anti-patterns (blocking - must reject)
- [ ] silent failures - empty except blocks, no logging
- [ ] god functions - >30 lines or >3 params
- [ ] god classes - >7 public methods
- [ ] global variables - use dependency injection
- [ ] walrus operators - complex one-liners violate simplicity
- [ ] magic numbers/strings - use named constants
- [ ] sql injection - f-strings in queries instead of parameterized
- [ ] missing error context - bare exceptions without detail
- [ ] missing tests - new api endpoints, new blocks, bug fixes must have tests

### code quality (should fix)
- [ ] specific exceptions caught (never bare `Exception` without re-raise)
- [ ] `logger.exception()` preserves stack traces
- [ ] error messages include context dict
- [ ] parameterized queries always (`?` placeholders, never f-strings)
- [ ] transactions for multi-step database operations
- [ ] async I/O used (aiofiles, aiosqlite - no blocking calls)
- [ ] `asyncio.gather` for concurrent operations
- [ ] background tasks cancelled in cleanup
- [ ] pydantic models for API request validation
- [ ] consistent error response format
- [ ] dependency injection for services
- [ ] size limits on file uploads
- [ ] type hints on all parameters and returns
- [ ] `| None` instead of `Optional`
- [ ] entities used instead of big dicts (>5 fields)

### testing
- [ ] blocking: new api endpoints must have tests
- [ ] blocking: new blocks must have unit tests
- [ ] blocking: bug fixes must have regression tests
- [ ] error cases tested (not just happy path)
- [ ] test names: `test_<method>_<scenario>_<expected>`
- [ ] one behavior per test

### security
- [ ] no secrets in logs
- [ ] all inputs validated at API boundary
- [ ] size limits enforced
- [ ] SQL queries parameterized

---

## frontend checklist

### anti-patterns (blocking - must reject)
- [ ] silent error handling - empty catch blocks
- [ ] bloated components - too many hooks, mixed concerns
- [ ] prop drilling - >5 props passed through multiple levels
- [ ] repeated JSX - copied 3+ times without extraction
- [ ] direct storage access - localStorage/sessionStorage not abstracted
- [ ] inline fetch calls - not in service layer
- [ ] unstable dependencies - missing useCallback/useMemo in hooks
- [ ] missing cleanup - useEffect without return for intervals/subscriptions/AbortController
- [ ] any types - use proper types or `unknown`
- [ ] type assertions - `as` instead of type guards
- [ ] hardcoded colors - use theme variables (fg.*, canvas.*, border.*) not #000, #fff, rgb()

### code quality (should fix)
- [ ] components focused (extract if unwieldy)
- [ ] max 5 props per component (use context for more)
- [ ] related state grouped (useReducer for complex state)
- [ ] no direct localStorage (use custom hooks)
- [ ] stable dependencies (useCallback for functions in deps)
- [ ] cleanup functions returned from effects
- [ ] AbortController for fetch calls
- [ ] mounted flags for async operations
- [ ] useMemo for expensive calculations
- [ ] API calls through service layer
- [ ] custom hooks for data fetching
- [ ] error handling with user feedback
- [ ] loading states shown
- [ ] errors logged to console
- [ ] user feedback for failures (toast/flash/modal)
- [ ] error boundaries used
- [ ] nullable values handled properly

### typescript
- [ ] no `any` types
- [ ] no `as` assertions (use type guards)
- [ ] all props have interfaces
- [ ] proper handling of null/undefined

### performance
- [ ] expensive calculations use useMemo
- [ ] callbacks use useCallback
- [ ] React.memo where appropriate
- [ ] heavy components lazy loaded

### testing
- [ ] business logic extracted from components
- [ ] API calls mockable
- [ ] tests exist for new features

### ui/ux
- [ ] theme compatibility verified in both light and dark modes
- [ ] text uses fg.* colors (fg.default, fg.muted, fg.subtle)
- [ ] backgrounds use canvas.* colors
- [ ] no hardcoded colors (#000, #fff, rgb())
- [ ] interactive states work in both themes

---

## documentation updates

### when to update llm/state-*.md files

llm/state-backend.md - update when:
- new API endpoints added or changed
- database schema modified
- new blocks added to lib/blocks/
- core logic patterns changed (workflow, storage, job processing)
- error handling patterns changed

llm/state-frontend.md - update when:
- new pages or components added
- UI flow changed
- state management patterns changed
- API integration patterns changed
- routing updated

llm/state-project.md - update when:
- overall architecture changed
- new major features added
- file structure reorganized
- testing patterns changed
- deployment process changed

### what to document
- describe what changed and why
- explain new patterns introduced
- note any breaking changes
- keep it concise and technical
- update gradually, not complete rewrites
- reflect actual code, not aspirational designs

### code comments
- [ ] complex logic has comments explaining why (not what)
- [ ] comments are lowercase and concise
- [ ] no over-documentation of obvious code

---

## refactoring reviews

when reviewing refactoring changes (identified by large-scale file changes or systematic pattern updates):

### what to expect
- many files changed (pattern harmonization)
- file renames and moves (following refactoring plan)
- function/variable renames for consistency
- code moved to better locations
- duplicate patterns consolidated

### what to verify
- [ ] pattern choice is correct - chosen pattern is actually dominant in codebase (count occurrences)
- [ ] tests still pass - no functionality broken
- [ ] anti-patterns removed - not just moved around
- [ ] documentation updated - llm/state-*.md files reflect changes
- [ ] quality improved - code is simpler, clearer, more consistent
- [ ] behavior unchanged - unless explicitly documented
- [ ] no scope creep - refactoring doesn't include new features

### acceptable
- renaming for consistency
- moving code to better locations
- consolidating duplicates
- extracting reusable components
- breaking up large functions

### not acceptable
- new anti-patterns while fixing old ones
- breaking tests without fixing
- changing behavior without docs
- mixing refactoring with features
- adding complexity while claiming to simplify

---

## review process

### step 1: anti-pattern scan
scan code for anti-patterns from checklists above. flag immediately if found.

backend: silent failures, god functions, sql injection, magic numbers
frontend: silent errors, bloated components, prop drilling, inline fetch

### step 2: security check
verify no security vulnerabilities:
- SQL injection (parameterized queries)
- XSS (proper escaping)
- missing input validation
- secrets in logs
- missing size limits

### step 3: code quality review
apply relevant checklist items:
- error handling proper
- type hints complete
- proper async/await usage
- dependency injection used
- tests exist

### step 4: documentation check
identify which llm/state-*.md files need updates:
- new patterns → document them
- changed architecture → update state files
- complex logic → add why comments

### step 5: testing verification
- new features have tests
- error cases covered
- test names follow convention

---

## output format

```markdown
### anti-patterns found
[if none: "none found"]

1. [name]
- location: file:line
- violation: specific anti-pattern from checklist
- why: which rule violated
- fix: concrete suggestion

### security issues
[if none: "none found"]

### documentation updates required
[if none: "none required"]

1. [change description]
- file: llm/state-backend.md | llm/state-frontend.md | llm/state-project.md
- section: specific section to update
- reason: what changed
- details: what to document

### code quality issues
[if none: "none found"]

- severity: critical | high | medium | low
- location: file:line
- issue: description
- fix: concrete suggestion

### testing gaps
[if none: "none found"]

### recommendations
[optional improvements]

### summary
- anti-patterns: ✓ none | ✗ found (count)
- security: ✓ clean | ✗ issues (count)
- documentation: ✓ current | ⚠ updates needed
- testing: ✓ covered | ⚠ gaps exist
- code quality: ✓ good | ⚠ issues exist

### verdict
[block | request changes | approve]

reason: [brief explanation]
```

---

## examples

### example 1: blocking anti-pattern

```markdown
### anti-patterns found

1. silent failure
- location: frontend/Review.tsx:112
- violation: empty catch block
- why: violates "fail loudly" principle (frontend checklist)
- fix: `catch (err) { console.error(err); showToast({type: "error", message: err.message}); }`

### verdict
block - must fix silent error handling before merge
```

### example 2: documentation update needed

```markdown
### anti-patterns found
none found

### documentation updates required

1. new validation pattern
- file: llm/state-backend.md
- section: validation patterns
- reason: added parameterized query validation in api.py
- details: document how user input is sanitized using parameterized queries

### verdict
request changes - update state-backend.md to document new pattern
```

### example 3: refactoring review

```markdown
### anti-patterns found
none found

### documentation updates required

1. harmonized error handling
- file: llm/state-backend.md
- section: error handling patterns
- reason: standardized all blocks to use logger.error() + raise pattern
- details: document chosen pattern and why (used in 8/10 blocks)

### summary
- anti-patterns: ✓ none
- security: ✓ clean
- documentation: ⚠ updates needed
- testing: ✓ all passing
- code quality: ✓ improved (error handling now consistent)

refactoring verified:
- ✓ pattern choice correct (dominant in codebase)
- ✓ tests passing
- ✓ anti-patterns removed
- ✓ quality improved

### verdict
request changes - update state-backend.md then approve
```

---

## golden rules

1. anti-patterns are blocking - always reject
2. security issues are blocking - always reject
3. broken tests are blocking - always reject
4. llm/* updates required - for architecture changes
5. simplicity wins - if code is complex, it's wrong
6. fail loudly - silent failures are never acceptable
7. self-contained - all rules in this file, don't read external files
