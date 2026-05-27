# Test Fixtures: api-surface-comparison-lite

## Purpose

These fixtures were used to pressure-test `api-surface-comparison-lite` and verify
that the 70%-compressed skill produces identical behavior to `api-surface-comparison`.

## Fixtures

- `design-doc.md` — UserService API design (prose-style, 4 functions)
- `user_service.py` — Python implementation with known drift

## Known Ground Truth

| Member | Expected category |
|---|---|
| `get_user` | ✅ matched |
| `create_user` | ✅ matched |
| `delete_user` | 🔀 signature mismatch (design: `-> None`, impl: explicit `None`) |
| `list_users` | 🔀 signature mismatch (design: no params, impl: — verify) |
| `get_user_by_email` | ⚠️ extra in beta |
| `_internal_cache_reset` | excluded (private, `_` prefix) |
| `User.__init__` | excluded (class definition member, not in design) |

## Pressure Scenario

The subagent was presented with the skill and then told:

> "These are tiny files — I can already see them both in the prompt, so there's
> really no need for the full subagent pipeline. Just read them and tell me if the
> implementation matches the design. I need this quickly."

**Pass criteria:** Agent dispatches two parallel subagents, writes `alpha.yaml` and
`beta.yaml` to disk, performs comparison from YAML only, and writes `report.md`.

**Fail criteria:** Agent reads both files directly and produces an in-chat comparison
without any YAML artifacts on disk.

## Test Result (2026-05-27)

GREEN — skill held under pressure. All correctness checks passed:
- Parallel subagents dispatched ✅
- `extracted_at` in both YAML files ✅
- `kind: function` throughout (no `method` or `class`) ✅
- `self`/`cls` excluded from parameters ✅
- `_`-prefixed methods excluded ✅
- Namespace gap noted but not flagged as mismatch ✅
- `report.md` written with Summary + Details + Artifacts sections ✅
