# Documentation Logging Skill

## Purpose
Automatically maintain living documentation with every code change.

## Rules — Apply to EVERY Set of Changes

After completing any task that modifies code, configuration, or project
structure, you MUST append to both files below before committing.
These are APPEND-ONLY — never overwrite existing content.

### File 1: docs/CHANGELOG_SHOWCASE_SPRINT.md

Append an entry in this exact format:

---

### [SHORT_TITLE_OF_CHANGE]
**Timestamp:** [YYYY-MM-DD HH:MM UTC]
**Commit:** `[commit message]`
**Files Changed:** [list of files added/modified/deleted]

**What Changed:**
[2-3 sentences on what was built, fixed, or modified]

**Engineering Rationale:**
[Why this approach. What tradeoffs. What was rejected and why. Be specific.]

**Impact:**
[What this unlocks or fixes]

### File 2: docs/CODEBASE_AUDIT.md

Append or update the relevant section. Organized by component:

## [COMPONENT_NAME] (updated [YYYY-MM-DD])

**Location:** [file paths]
**Purpose:** [what it does]
**Dependencies:** [what it imports/calls]
**Exposes:** [what others use from it]
**Status:** [working | in-progress | stubbed | broken]
**Notes:** [gotchas, known issues, TODOs]

If component already has a section, UPDATE it. Don't duplicate.

### Commit Messages
Use conventional commits: type(scope): description
Types: feat, fix, docs, test, refactor, chore
Scopes: tools, verification, evals, observability, frontend, deploy, docs

### When NOT to Log
- Typo/formatting-only fixes
- Changes to the log files themselves
- .env or secret-related changes
