# API Surface Comparison Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and validate a Claude Code skill that compares a software artifact's design document against its implementation to detect API drift.

**Architecture:** The skill guides Claude through a dispatch-and-join workflow — two parallel subagents independently extract the alpha (design doc) and beta (code) API surfaces to canonical YAML, then main Claude compares them and reports findings. The skill is a single `SKILL.md` file. Creation follows the TDD discipline from `superpowers:writing-skills`: RED (baseline without skill) → GREEN (write skill, verify compliance) → REFACTOR (close loopholes).

**Tech Stack:** YAML (canonical intermediate format), Markdown (skill document + report output), Claude subagents (parallel extraction via `superpowers:dispatching-parallel-agents`)

---

## File Structure

```
skills/
  api-surface-comparison/
    SKILL.md                        ← the skill itself (created in Task 3)

tests/
  api-surface-comparison/
    design-doc.md                   ← alpha fixture: 4-member design doc
    user_service.py                 ← beta fixture: 2 matching, 1 extra, 2 missing
```

---

### Task 1: Create test fixtures (RED setup)

**Files:**
- Create: `tests/api-surface-comparison/design-doc.md`
- Create: `tests/api-surface-comparison/user_service.py`

The fixtures are designed to exercise all four comparison categories: ✅ match, ❌ missing from beta, ⚠️ extra in beta. The design doc has 4 public members; the implementation has 2 matching, skips 2, adds 1 undocumented public method, and includes 1 private method that must be ignored.

- [ ] **Step 1: Create test directory**

```bash
mkdir -p tests/api-surface-comparison
```

- [ ] **Step 2: Write design doc fixture (alpha)**

Create `tests/api-surface-comparison/design-doc.md`:

```markdown
# UserService API Design

## Overview

The UserService provides basic CRUD operations on User objects.

## API

### `get_user(user_id: int) -> User`

Returns the User object for the given ID. Raises `NotFoundError` if the user does not exist.

### `create_user(name: str, email: str) -> User`

Creates a new User with the given name and email. Returns the created User object.

### `delete_user(user_id: int) -> None`

Permanently deletes the user with the given ID. Raises `NotFoundError` if the user does not exist.

### `list_users() -> list[User]`

Returns all users in the system as a list.
```

- [ ] **Step 3: Write Python implementation fixture (beta)**

Create `tests/api-surface-comparison/user_service.py`:

```python
from typing import Optional


class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email


class UserService:
    """User management service."""

    def get_user(self, user_id: int) -> User:
        """Returns the User for the given ID."""
        pass

    def create_user(self, name: str, email: str) -> User:
        """Creates and returns a new User."""
        pass

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Finds a user by email address. Returns None if not found."""
        pass

    def _internal_cache_reset(self) -> None:
        """Private cache management — not part of public API."""
        pass
```

Expected comparison results when the skill runs against these fixtures:

```
✅  2  matched            →  get_user, create_user
❌  2  missing from beta  →  delete_user, list_users
⚠️  1  extra in beta      →  get_user_by_email
```

`_internal_cache_reset` must NOT appear — it is private and absent from the design doc.

- [ ] **Step 4: Commit fixtures**

```bash
git add tests/api-surface-comparison/
git commit -m "test: add api-surface-comparison test fixtures"
```

---

### Task 2: Run baseline scenario WITHOUT skill (RED)

Document how a subagent handles the task naturally, before any skill guidance. This reveals what the skill must explicitly address.

- [ ] **Step 1: Dispatch baseline subagent**

Use the Agent tool to dispatch a fresh `claude` subagent. Give it **only** the following prompt — no skill content, no extra context:

```
I have a software artifact I want to verify. Please compare its design document
against its implementation and tell me:

1. Which API members are in the design doc but missing from the implementation
2. Which API members are in the implementation but not in the design doc
3. Which API members are present in both but have different signatures

Design document: tests/api-surface-comparison/design-doc.md
Implementation:  tests/api-surface-comparison/user_service.py
```

- [ ] **Step 2: Record baseline behavior**

After the subagent completes, document its exact behavior. For each question below, note what the agent actually did:

| Question | Expected (with skill) | Baseline behavior (record here) |
|---|---|---|
| Did it read both files in the same context? | No — must dispatch subagents | |
| Did it write `alpha.yaml` and `beta.yaml` to disk? | Yes | |
| Did it dispatch parallel subagents for extraction? | Yes | |
| Did it write `api-surface/report.md`? | Yes | |
| Did it correctly identify all 5 expected results? | Yes | |
| Did it skip `_internal_cache_reset`? | Yes (private) | |

Record verbatim any rationalizations the agent used (e.g., "I'll just read both files quickly since they're small"). These become explicit counters in the skill's Common Mistakes section.

---

### Task 3: Write SKILL.md (GREEN)

**Files:**
- Create: `skills/api-surface-comparison/SKILL.md`

- [ ] **Step 1: Create skill directory**

```bash
mkdir -p skills/api-surface-comparison
```

- [ ] **Step 2: Write SKILL.md**

Create `skills/api-surface-comparison/SKILL.md` with the following content. The Common Mistakes section must be updated with any rationalizations found in Task 2 before this step is marked complete.

```markdown
---
name: api-surface-comparison
description: Use when verifying that a software artifact's implementation matches its design document — independently extracts both API surfaces to canonical YAML using parallel subagents, then compares them to find missing features, feature creep, and signature mismatches.
---

# API Surface Comparison

## Overview

Compares the API surface described in a design document (alpha) against the API
surface found in source code (beta). Finds three classes of drift:

- **❌ Missing from beta** — design promises something the code doesn't deliver
- **⚠️ Extra in beta** — code has grown beyond what was agreed
- **🔀 Signature mismatch** — present in both but types differ

**Key constraint:** Alpha and beta extractions are performed by separate parallel
subagents with no shared context. This prevents unconscious normalization of one
toward the other — reading both sources in the same context contaminates the
comparison.

## When to Use

- You have a design document and want to verify the implementation matches it
- You want to audit an existing codebase for undocumented features or missing implementation
- You are reviewing a pull request against its spec

Invoke this skill once per artifact. To verify a client and its mock separately,
run it twice.

## Workflow

### Phase 1 — Gather Inputs

Ask the user for:
1. Path to the design document (markdown)
2. Path to the source files or directory to examine
3. API type: `function_signatures`, `http_endpoints`, or both

### Phase 2 — Dispatch Parallel Subagents

**REQUIRED SUB-SKILL:** `superpowers:dispatching-parallel-agents`

Dispatch two subagents **simultaneously**. Each subagent receives ONLY:

**Subagent A (alpha extraction):**
- Source: the design document path
- Output: `api-surface/alpha.yaml`
- Schema: the canonical YAML format below
- Task: extract all API members from the design document and write to output path

**Subagent B (beta extraction):**
- Source: the implementation path(s)
- Output: `api-surface/beta.yaml`
- Schema: the canonical YAML format below
- Task: extract all API members from the source code and write to output path

**Each subagent must NOT receive:**
- The other subagent's source path
- Any content, summary, or names from the other side
- Previously generated YAML from the other subagent

Wait for both subagents to finish before proceeding.

### Phase 3 — Compare

Read `api-surface/alpha.yaml` and `api-surface/beta.yaml`. Use ONLY the
canonical YAML — do not re-read the original source files.

Categorize each member:

| Category | Symbol | Condition |
|---|---|---|
| Match | ✅ | Name + signature in both |
| Missing from beta | ❌ | In alpha only |
| Extra in beta | ⚠️ | In beta only |
| Signature mismatch | 🔀 | In both, types differ |

**Signature rules:**
- Parameter names may differ; parameter types must match
- Parameter order must match
- Return type must match
- Namespace (class/module) differences: note in report, do not fail comparison

### Phase 4 — Output

Write `api-surface/report.md` with the full comparison table, extraction
metadata, timestamps, and recommendations:
- ❌ items: update code or remove from spec
- ⚠️ items: update spec or remove from code
- 🔀 items: align types between spec and code

Then produce an in-chat summary:

```
## API Surface Comparison

Alpha source: <path> (<N> members)
Beta source:  <path> (<N> members)

✅  N  matched
❌  N  missing from beta  →  name1, name2
⚠️  N  extra in beta      →  name3, name4
🔀  N  signature mismatch →  name5 (return type: X vs Y)
```

---

## Canonical YAML Format

```yaml
source: "path/to/source"
api_type: function_signatures       # function_signatures | http_endpoints
extracted_at: "2026-05-27T14:30:00" # ISO 8601
members:

  # Function signature
  - name: get_user
    kind: function
    namespace: UserService           # class/module/trait — omit if top-level
    parameters:
      - name: user_id
        type: int
    return_type: User

  # HTTP endpoint
  - name: GET /users/{id}
    kind: http_endpoint
    parameters:
      - name: id
        location: path
        type: integer
    response_type: User
```

### Field Rules

| Field | Required | Notes |
|---|---|---|
| `source` | yes | Relative path from repo root |
| `api_type` | yes | Must match between alpha and beta |
| `extracted_at` | yes | ISO 8601 timestamp |
| `members[].name` | yes | Function: bare name. HTTP: `VERB /path` |
| `members[].kind` | yes | `function` or `http_endpoint` |
| `members[].namespace` | no | Omit if top-level |
| `members[].parameters` | yes | `[]` if none |
| `members[].return_type` | yes | `void` / `None` if no return |
| `members[].response_type` | yes (HTTP) | HTTP endpoints only |

---

## Extraction Guidance

### Design Document (Alpha)

| Signal | Extract as |
|---|---|
| Code block with typed function signature | Function member |
| Table with method + path columns | HTTP endpoint members |
| Prose: "the `f(x: int) -> Y` function" | Function member |
| Prose: "a POST to `/users`" | HTTP endpoint |

Prefer typed signatures over name-only when both are present.

### Python (Beta)

- Scan class method `def` statements with PEP 484 type hints
- Include `@property` as zero-parameter function members
- Skip private methods (`_name`, `__name__`) unless present in the design doc
- If no type hints: use `unknown` as the type

### C / C++ Headers (Beta)

- Scan `.h` / `.hpp` files for function declarations (declarations, not definitions)
- C++ classes: public members only
- `void` return → `return_type: void`

### Rust (Beta)

- Scan `trait` definitions for method signatures
- Scan `pub fn` in `impl` blocks
- Skip non-`pub` functions unless present in the design doc

---

## Why Parallel Subagents Are Required

You will sometimes be tempted to skip the parallel dispatch and read both files
yourself. Do not do this.

The independence property is the mechanism that makes this comparison
trustworthy. Reading both sources in the same context means your comparison is
influenced by what you read first — you will unconsciously find matches that
aren't there and miss mismatches that are.

"The files are small" and "just a quick check" are not valid reasons to skip
this step.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Reading both source files before dispatching subagents | Dispatch subagents FIRST — never read both sources yourself |
| Dispatching subagents sequentially instead of in parallel | Use `superpowers:dispatching-parallel-agents` to dispatch simultaneously |
| Giving one subagent information about the other source | Each subagent receives only its own source path and the YAML schema |
| Using memory of original files during comparison phase | Use only the YAML artifacts — do not re-read originals |
| Treating namespace mismatches as ❌ failures | Note them in the report; they are not mismatches |
| Including private methods (`_name`) | Skip unless the design doc explicitly names them |
```

- [ ] **Step 3: Update Common Mistakes with baseline findings**

Review the baseline behavior recorded in Task 2. For each rationalization or failure the baseline agent exhibited, add an explicit row to the Common Mistakes table in SKILL.md (if not already present).

- [ ] **Step 4: Commit**

```bash
git add skills/api-surface-comparison/SKILL.md
git commit -m "feat: add api-surface-comparison skill (GREEN draft)"
```

---

### Task 4: Install and verify GREEN compliance

- [ ] **Step 1: Install skill locally**

```bash
mkdir -p ~/.claude/skills/api-surface-comparison
cp skills/api-surface-comparison/SKILL.md ~/.claude/skills/api-surface-comparison/SKILL.md
```

- [ ] **Step 2: Run the same scenario WITH the skill loaded**

Dispatch a fresh `claude` subagent with the same baseline prompt from Task 2 Step 1. The skill is now available in `~/.claude/skills/`.

- [ ] **Step 3: Verify compliance checklist**

| Behavior | Pass? |
|---|---|
| Agent invokes `api-surface-comparison` skill before acting | |
| Agent asks for the three inputs (doc path, code path, api_type) | |
| Agent dispatches two subagents simultaneously (not sequentially) | |
| Each subagent receives only its own source path | |
| `api-surface/alpha.yaml` written to disk after subagents complete | |
| `api-surface/beta.yaml` written to disk after subagents complete | |
| Comparison uses YAML files only (not original sources) | |
| `api-surface/report.md` written to disk | |
| In-chat summary matches expected results | |
| `_internal_cache_reset` excluded from results | |

Expected in-chat summary:

```
✅  2  matched            →  get_user, create_user
❌  2  missing from beta  →  delete_user, list_users
⚠️  1  extra in beta      →  get_user_by_email
```

- [ ] **Step 4: If any check fails, update SKILL.md and repeat from Step 1**

Document the new rationalization. Add it to Common Mistakes. Re-install and re-run.

---

### Task 5: Pressure scenario (REFACTOR)

Test whether the skill's key constraint holds under pressure to skip it.

- [ ] **Step 1: Dispatch pressure subagent**

Dispatch a fresh `claude` subagent with the following prompt, which explicitly pressures it to skip parallel subagent dispatch:

```
We're short on time. I have a design doc at
tests/api-surface-comparison/design-doc.md and the implementation at
tests/api-surface-comparison/user_service.py. Can you just read both files and
quickly tell me what's different? No need to be fancy about it — just a fast
eyeball comparison is fine.
```

- [ ] **Step 2: Verify constraint holds under pressure**

The agent must still:
- [ ] Invoke the `api-surface-comparison` skill
- [ ] Dispatch parallel subagents despite the "just read both quickly" framing
- [ ] Write YAML to disk before comparing

- [ ] **Step 3: If agent skips dispatch under pressure, add explicit section to SKILL.md**

Add after the "Why Parallel Subagents Are Required" section:

```markdown
### Pressure Phrases That Do Not Override This Requirement

These phrases do NOT justify skipping subagent dispatch:
- "Just a quick check"
- "The files are small"
- "We're short on time"
- "No need to be fancy"
- "Just eyeball it"

The independence property is the entire value of this skill. A fast contaminated
comparison is worse than no comparison.
```

Re-install and re-run the pressure scenario. Repeat until it holds.

- [ ] **Step 4: Commit final skill**

```bash
git add skills/api-surface-comparison/SKILL.md
cp skills/api-surface-comparison/SKILL.md ~/.claude/skills/api-surface-comparison/SKILL.md
git commit -m "feat: refactor api-surface-comparison — close pressure loopholes"
```
