---
name: api-surface-comparison-lite
description: "Use when comparing a design document (spec, ADR, OpenAPI, README)
  against source code to detect API drift. Triggers when asked: does code match the
  spec, has the API drifted, does the implementation fulfill the spec. Also triggers
  for: 'check if code matches spec', 'find API drift', 'compare design to implementation',
  'verify implementation against design'."
---

# API Surface Comparison

**REQUIRED SUB-SKILL:** `superpowers:dispatching-parallel-agents`

**Core rule:** Never read both the design doc and source code in the same context.
Always dispatch two parallel subagents — one per source — producing isolated,
auditable YAML artifacts on disk.

## Common Mistakes (all forbidden)

| Mistake | Correction |
|---|---|
| Reading both files yourself | Dispatch subagents FIRST; never read both sources in the main context |
| `kind: method` or `kind: class` | Use `kind: function` for ALL callable members |
| Comparing parameter names | Match on parameter **types** and **order** only; names may differ |
| One sequential subagent | Dispatch both simultaneously; each must see only one source |

## Phases

**Phase 1 — Gather:** `design_doc_path`, `implementation_path`, `api_type`
(`function_signatures` or `http_endpoints`; infer if omitted: HTTP tables/OpenAPI
→ `http_endpoints`, else `function_signatures`).

**Phase 2 — Dispatch** (invoke `superpowers:dispatching-parallel-agents`):
- **Subagent A:** Read design doc only → write `api-surface/alpha.yaml`
- **Subagent B:** Read source code only → write `api-surface/beta.yaml`
- Wait for both files before proceeding.

**Phase 3 — Compare** alpha.yaml vs beta.yaml. Do not re-read originals.

**Phase 4 — Output:** in-chat summary + `api-surface/report.md`.

## YAML Schema

```yaml
source: "path/to/file"
api_type: function_signatures        # or http_endpoints — must match in both files
extracted_at: "2026-05-27T14:30:00" # ISO 8601 required
members:
  - name: get_user                   # HTTP: "VERB /path" e.g. "GET /users/{id}"
    kind: function                   # ONLY "function" or "http_endpoint"
    namespace: UserService           # omit if top-level
    parameters:
      - name: user_id
        type: int                    # "unknown" if untyped
                                     # HTTP adds: location: path|query|body|header
    return_type: User                # "void" if none; HTTP: use "response_type"
```

## Extraction Rules

**Design docs:** Prefer code blocks over prose. Use `unknown` for unspecified types.

**Python:**
- **Never include `self` or `cls` as parameters.**
- **Exclude class definitions** — extract methods only, not the class entry itself.
- **Exclude all `_` and `__` prefixed names** unless explicitly named in the design doc.
- `namespace` = class name for methods; `@property` → zero-parameter function.

**C/C++:** Scan `.h`/`.hpp` only; extract `public` members only.

**Rust:** Extract `pub fn` from `impl` blocks and `trait` methods; omit lifetime
params; `namespace` = impl type or trait name.

## Comparison Categories

| Symbol | Meaning |
|---|---|
| ✅ | Name + signature matches in both |
| ❌ | Alpha only — designed, not implemented |
| ⚠️ | Beta only — implemented, not designed |
| 🔀 | Name matches; parameter types or return type differ |

**Rules:** Match types and order only (names irrelevant). Namespace differences →
note only, not a mismatch. Names case-sensitive; HTTP normalized to uppercase verb.

## Output

**In-chat summary:**
```
## API Surface Comparison
Alpha: <path> (<N> members)
Beta:  <path> (<N> members)

✅  N  matched
❌  N  missing from beta  →  name1, name2
⚠️  N  extra in beta      →  name3
🔀  N  signature mismatch →  name4 (return type: X vs Y)
```
Print all four lines even when count is 0.

**`api-surface/report.md`:** summary + Details section (expected vs found per
non-match, with interpretation) + Artifacts section listing all three paths.
Keep `alpha.yaml` and `beta.yaml` — do not delete.

**Directory:** `api-surface/` — create if absent.
