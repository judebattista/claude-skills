---
name: api-surface-comparison
description: "Use when comparing a software artifact's design document against its source code implementation to detect API drift. Triggers when a user provides a design doc (spec, ADR, OpenAPI file, README) and an implementation (source file or directory) and asks whether the code matches the design, whether the API has drifted, or whether the implementation fulfills the spec. Also triggers for phrases like 'check if code matches spec', 'find API drift', 'compare design to implementation', or 'verify implementation against design'."
---

# API Surface Comparison Skill

This skill guides Claude through a structured, parallel-subagent workflow for comparing an API design document (alpha) against a source code implementation (beta) to detect API drift. The output is both an in-chat summary and a written report file.

**Required sub-skill:** `superpowers:dispatching-parallel-agents`

---

## Why Parallel Subagents Are Required

The single most important rule of this skill:

> **You must NOT read both the design doc and the source code in the same Claude context and compare them conversationally.**

This naive pattern — "I'll just read both files directly" — is explicitly forbidden. It produces unreliable results because:

1. A single context sees both sources simultaneously and conflates detail from each, producing hallucinated matches.
2. It produces no durable artifacts (no YAML files on disk, no report file).
3. It cannot be audited or re-run independently.
4. It treats the task as a reading exercise rather than a structured extraction + comparison pipeline.

The correct process always uses **two independent subagents dispatched in parallel**, each seeing only one source. Their outputs are YAML files written to disk. The main Claude agent reads those YAML files and performs the comparison. This is not optional.

---

## Common Mistakes

The following mistakes have been observed in baseline (unskilled) attempts. All are forbidden.

| Mistake | Why It Is Forbidden |
|---|---|
| Reading both files in the same Claude context | Produces conflation and hallucinated matches; no auditable extraction |
| Comparing conversationally without writing YAML | No durable extraction artifact; cannot be verified or re-run |
| Never dispatching subagents | Bypasses the parallel isolation that makes comparison reliable |
| Not writing a report file | Output lives only in chat; cannot be referenced later |
| Using one subagent sequentially rather than two in parallel | Violates isolation; later subagent can be influenced by first |
| Skipping private method exclusion in Python | Over-reports beta surface; inflates "extra in beta" count |
| Omitting `extracted_at` timestamp | Breaks schema; makes artifact non-auditable |
| Comparing parameter names instead of types | Produces false mismatches when names differ but types match |

---

## Workflow Overview

The workflow has four phases. All phases must be completed; no phase may be skipped.

```
Phase 1: Gather Inputs
Phase 2: Dispatch Parallel Subagents → alpha.yaml + beta.yaml (written to disk)
Phase 3: Compare YAML Files → categorize each member
Phase 4: Output → in-chat summary + api-surface/report.md
```

---

## Phase 1: Gather Inputs

Collect the following from the user before proceeding:

| Input | Description | Required |
|---|---|---|
| `design_doc_path` | Path to the design document (alpha) | Yes |
| `implementation_path` | Path to the source code file or directory (beta) | Yes |
| `api_type` | Extraction mode: `function_signatures` or `http_endpoints` | Yes |

If `api_type` is not specified, infer from context: if the design doc contains HTTP method/path tables or OpenAPI-style entries, use `http_endpoints`; otherwise use `function_signatures`.

---

## Phase 2: Dispatch Parallel Subagents

Invoke `superpowers:dispatching-parallel-agents` to launch **two subagents simultaneously**:

**Subagent A (alpha extractor):**
- Input: `design_doc_path`, `api_type`
- Task: Read only the design document. Extract all API members. Write the result to `api-surface/alpha.yaml` using the canonical YAML format below.
- Constraint: Must not read or reference the implementation source.

**Subagent B (beta extractor):**
- Input: `implementation_path`, `api_type`
- Task: Read only the source code. Extract all API members. Write the result to `api-surface/beta.yaml` using the canonical YAML format below.
- Constraint: Must not read or reference the design document.

Both subagents must complete and write their YAML files before Phase 3 begins.

---

## Canonical YAML Format

Both `alpha.yaml` and `beta.yaml` must use this exact schema:

```yaml
source: "path/to/source"
api_type: function_signatures
extracted_at: "2026-05-27T14:30:00"
members:
  - name: get_user
    kind: function
    namespace: UserService
    parameters:
      - name: user_id
        type: int
    return_type: User
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
| `source` | Yes | Relative path from repo root |
| `api_type` | Yes | Must match between alpha.yaml and beta.yaml |
| `extracted_at` | Yes | ISO 8601 timestamp |
| `members[].name` | Yes | Functions: bare name. HTTP: `VERB /path` |
| `members[].kind` | Yes | `function` or `http_endpoint` |
| `members[].namespace` | No | Omit if member is top-level (not in a class/module) |
| `members[].parameters` | Yes | Use `[]` if the member takes no parameters |
| `members[].return_type` | Yes (functions) | Use `void` or `None` if no return value |
| `members[].response_type` | Yes (HTTP endpoints) | The type of the response body |
| `parameters[].name` | Yes | Parameter name as written in source |
| `parameters[].type` | Yes | Type as written; use `unknown` if untyped |
| `parameters[].location` | HTTP only | `path`, `query`, `body`, or `header` |

---

## Phase 3: Compare YAML Files

The main Claude agent reads `api-surface/alpha.yaml` and `api-surface/beta.yaml`. Do not re-read the original source files. Compare using the following categories:

| Category | Symbol | Definition |
|---|---|---|
| Match | ✅ | Member name present in both alpha and beta with matching signature |
| Missing from beta | ❌ | Member in alpha only — designed but not implemented |
| Extra in beta | ⚠️ | Member in beta only — implemented but not designed |
| Signature mismatch | 🔀 | Member name in both, but parameter types or return type differ |

### Signature Comparison Rules

- **Parameter names may differ; parameter types must match.**
- **Parameter order must match.**
- **Return type must match** (for functions) or **response type must match** (for HTTP endpoints).
- **Namespace differences**: note in the report but do not classify as a mismatch. A mismatch requires a type difference.
- Match on `members[].name` is case-sensitive for functions; HTTP endpoints match on normalized method + path (`GET /users/{id}` == `GET /users/{id}`, not `get /users/{id}`).

---

## Extraction Guidance

### Design Doc (Alpha)

Extract from any of these patterns:

| Pattern in design doc | What to extract |
|---|---|
| Code block containing typed function signatures | One `function` member per signature |
| Table with method column and path column | One `http_endpoint` member per row |
| Prose: "the `f(x: int) -> Y` function" | One `function` member with parsed signature |
| Prose: "a POST to `/users`" | One `http_endpoint` member |

Prefer typed information over name-only. If a signature appears both in prose and in a code block, use the code block version (more precise). If a parameter type is not stated anywhere in the design doc, use `unknown`.

### Python (Beta)

- Scan all `def` statements in the target file(s).
- Include class methods; set `namespace` to the class name.
- Include `@property` methods as zero-parameter `function` members.
- **Exclude** private methods: names starting with `_` or `__`, unless that name explicitly appears in the design doc.
- If a parameter lacks a PEP 484 type annotation, use `unknown` as its type.
- `self` and `cls` parameters are not API parameters; omit them.

### C/C++ Headers (Beta)

- Scan `.h` and `.hpp` files only; do not extract from `.c` or `.cpp` definition files.
- For C++ classes: extract `public` members only.
- `void` return type → set `return_type: void`.
- Template parameters: include in the member entry as a note field if they affect the signature.

### Rust (Beta)

- Scan `trait` definitions for method signatures; set `namespace` to the trait name.
- Scan `pub fn` declarations in `impl` blocks; set `namespace` to the impl type.
- **Exclude** non-`pub` functions unless the name explicitly appears in the design doc.
- Lifetime parameters are not API-surface parameters; omit them.
- If a function has no return type (`-> ()` or absent), use `return_type: void`.

---

## Phase 4: Output

### In-Chat Summary

After comparison is complete, print this summary in chat:

```
## API Surface Comparison

Alpha source: <design_doc_path> (<N> members)
Beta source:  <implementation_path> (<N> members)

✅  N  matched
❌  N  missing from beta  →  name1, name2
⚠️  N  extra in beta      →  name3, name4
🔀  N  signature mismatch →  name5 (return type: X vs Y)
```

List member names inline for each non-match category. If a category has zero items, still print the line with count 0.

### Report File

Write `api-surface/report.md` containing:

1. The in-chat summary table (copy verbatim).
2. A "Details" section with one subsection per non-match category.
3. Each detail entry: member name, what was expected (from alpha), what was found (from beta), and a brief interpretation.
4. A "Artifacts" section listing `alpha.yaml`, `beta.yaml`, and `report.md` with their paths.

Do not delete `alpha.yaml` or `beta.yaml` after writing the report; they are auditable artifacts.

---

## Directory Layout

All outputs go into `api-surface/` relative to the working directory:

```
api-surface/
  alpha.yaml    ← written by Subagent A
  beta.yaml     ← written by Subagent B
  report.md     ← written by main agent in Phase 4
```

Create the directory if it does not exist.
