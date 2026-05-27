# API Surface Comparison Skill — Design Spec

**Date:** 2026-05-27  
**Status:** Draft  
**Author:** jude + Claude

---

## Background & Motivation

Any piece of software with a design document has two representations of its API:

1. **The design document (alpha)** — what the API is *supposed* to be
2. **The implementation (beta)** — what the API *actually* is in code

Drift between these two is a common and costly problem:

- **Alpha has something beta doesn't** → an unimplemented feature; the design promises something the code doesn't deliver
- **Beta has something alpha doesn't** → feature creep or an underspecified design; the code has grown beyond what was agreed

This skill automates the detection of that drift for any single software artifact by independently extracting both API surfaces and comparing them.

**Usage pattern:** The skill is invoked once per artifact. 

**Key correctness constraint:** The two extractions must be **fully independent**. If a developer reviews both extractions before comparison, they may unconsciously normalize one toward the other, defeating the purpose of the check. Separate subagents with divergent contexts enforce this independence at the execution level.

---

## Skill Identity

- **Name:** `api-surface-comparison`
- **Description:** Use when verifying that a single software artifact's implementation matches its design document — dispatches parallel subagents to independently extract both API surfaces to canonical YAML, then compares them to find missing features, feature creep, and signature mismatches.
- **Target audience:** Small team (Python, C/C++, Rust)
- **Skill type:** Technique (concrete workflow with defined steps)

---

## Scope

### In scope
- REST endpoints (HTTP verb + path)
- Language-level function/method signatures (Python, C/C++ headers, Rust traits)
- Full signature comparison: name + parameter types + return type
- Parallel independent extraction via subagents
- Canonical YAML intermediate format written to disk
- In-chat summary + written comparison report

### Out of scope
- gRPC / Protobuf (future extension)
- Cross-artifact compatibility (e.g. client vs. mock) — separate skill
- Semantic comparison of docstrings or behavior
- Automatic remediation of discrepancies

---

## Workflow

### High-Level Flow

```
User invokes skill
      │
      ▼
Main Claude gathers inputs:
  - path to design document (alpha source)
  - path(s) to implementation code (beta source)
  - api_type: function_signatures | http_endpoints
      │
      ▼
Dispatch two subagents IN PARALLEL
  ┌───────────────────────┬───────────────────────┐
  │ Subagent A (alpha)    │ Subagent B (beta)      │
  │ reads: design doc     │ reads: codebase        │
  │ writes: alpha.yaml    │ writes: beta.yaml      │
  └───────────────────────┴───────────────────────┘
      │                           │
      └──────────── join ─────────┘
                    │
                    ▼
      Main Claude reads both YAML files
                    │
                    ▼
              Comparison
                    │
                    ▼
     In-chat summary + report.md
```

### Phase 1 — Input Gathering

Main Claude asks the user for:
- Path to the design document (markdown)
- Path(s) to the source files or directory to examine
- API type: `function_signatures` or `http_endpoints` (or both)

### Phase 2 — Parallel Extraction (Subagents)

Main Claude dispatches two subagents simultaneously using `superpowers:dispatching-parallel-agents`.

**Each subagent receives only:**
- Its source path
- The canonical YAML schema (see below)
- Its output file path (`api-surface/alpha.yaml` or `api-surface/beta.yaml`)
- Nothing about the other side

**Subagents must not be given:**
- The other subagent's source path
- Any information about what the other side is expected to contain
- Previously generated output from the other subagent

### Phase 3 — Comparison (Main Claude)

After both subagents complete, main Claude:
1. Reads `api-surface/alpha.yaml`
2. Reads `api-surface/beta.yaml`
3. Performs set comparison, categorizing each member

### Phase 4 — Output

- **In-chat summary:** counts by category + listing of all non-matching members
- **`api-surface/report.md`:** full comparison table, extraction metadata, timestamp

---

## Canonical YAML Format

Both `alpha.yaml` and `beta.yaml` conform to the same schema:

```yaml
source: "docs/design.md"           # path to source material
api_type: function_signatures       # function_signatures | http_endpoints
extracted_at: "2026-05-27T14:30:00"
members:

  # Function signature example
  - name: get_user
    kind: function
    namespace: UserClient           # class, module, trait, or service name
    parameters:
      - name: user_id
        type: int
    return_type: User

  # HTTP endpoint example
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
| `api_type` | yes | Must match between alpha and beta for a valid comparison |
| `extracted_at` | yes | ISO 8601 timestamp |
| `members[].name` | yes | For functions: bare name. For HTTP: `VERB /path` |
| `members[].kind` | yes | `function` or `http_endpoint` |
| `members[].namespace` | no | Omit if top-level / not applicable |
| `members[].parameters` | yes | Empty list `[]` if none |
| `members[].return_type` | yes | `void` / `None` if no return |
| `members[].response_type` | yes (HTTP) | For HTTP endpoints |

---

## Extraction Guidance per Source Type

### Design Document (Alpha)

| Signal | What to extract |
|---|---|
| Code blocks with function signatures | Parse directly as function members |
| API tables (columns: method, path, description) | Extract as HTTP endpoint members |
| Prose: "the `get_user(user_id: int)` function returns a `User`" | Extract function signature from prose |
| Prose: "a POST to `/users` creates a new user" | Extract HTTP endpoint |

When ambiguous, prefer the more specific form (typed signature > name only).

### Python (Beta)

- Scan class `__init__`, method `def` statements with type hints
- Capture PEP 484 annotations for parameter and return types
- If no type hints present, use `unknown` as the type
- Include `@property` as zero-parameter function members
- Skip private methods (`_name`, `__name__`) unless they appear in the design doc

### C / C++ Headers (Beta)

- Scan `.h` and `.hpp` files for function declarations
- Capture parameter types and return types from the declaration (not the implementation)
- For C++ classes, capture public member functions only
- Treat `void` return as `return_type: void`

### Rust (Beta)

- Scan `trait` definitions for method signatures
- Scan `pub fn` declarations in `impl` blocks
- Capture parameter types and return types
- Skip non-`pub` functions unless they appear in the design doc

---

## Comparison Categories

| Category | Symbol | Definition |
|---|---|---|
| Match | ✅ | Member in both alpha and beta with compatible signatures |
| Missing from beta | ❌ | In alpha but not beta — unimplemented feature |
| Extra in beta | ⚠️ | In beta but not alpha — feature creep or underspecification |
| Signature mismatch | 🔀 | Present in both but parameter types or return type differ |

### Signature Compatibility Rules

- Parameter names may differ; parameter **types** must match
- Parameter **order** must match
- Return type must match
- Namespace (class/module) differences are noted in the report but do not fail the comparison — a function with the same signature in a different namespace is still a ✅ Match, with the namespace difference called out separately

---

## Output Formats

### In-Chat Summary

```
## API Surface Comparison

Artifact: UserClient
Alpha source: docs/client-design.md (12 members)
Beta source:  src/client.py (14 members)

✅  9  matched
❌  2  missing from beta  →  create_user, delete_user
⚠️  3  extra in beta      →  internal_reset, _debug_dump, legacy_get
🔀  1  signature mismatch →  get_user (return type: User vs UserDTO)
```

### report.md

Full comparison table with:
- All members from both sides, categorized
- Exact signatures where mismatches occur
- Extraction metadata (source paths, timestamps, api_type)
- Recommendations:
  - ❌ items: missing implementation — update code or remove from spec
  - ⚠️ items: undocumented implementation — update spec or remove from code
  - 🔀 items: signature drift — align types between spec and code

---

## Required Sub-Skills

- **REQUIRED:** `superpowers:dispatching-parallel-agents` — used to dispatch alpha and beta extraction subagents simultaneously with divergent contexts

---

## File Layout

```
api-surface/
  alpha.yaml       ← written by Subagent A
  beta.yaml        ← written by Subagent B
  report.md        ← written by main Claude after comparison

docs/superpowers/specs/
  2026-05-27-api-surface-comparison-skill-design.md  ← this file
```

---

## Future Extensions

- gRPC / Protobuf support (add `rpc_method` as a `kind`)
- Cross-artifact compatibility skill: compare alpha.yaml from one artifact against beta.yaml from another (e.g. client vs. mock)
- Snapshot diffing: compare today's `alpha.yaml` against a previous committed version to track spec drift over time
