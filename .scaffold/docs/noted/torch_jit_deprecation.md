# torch.jit Deprecation on Python 3.14+

**Status**: Acknowledged — 28 warnings, no failures
**Severity**: Low (tests pass, production path unaffected)
**Resolution target**: After S33 (end of session roadmap)

## Symptom

`pytest .scaffold/tests/` emits 28 `DeprecationWarning`s from:
- `torch.jit.trace` — `test_ml_export.py`, `test_ml_model_io.py`
- `torch.jit.trace_method` — same files
- `torch.jit.load` — same files

Message: *"torch.jit.trace is not supported in Python 3.14+ and may
break. Please switch to torch.compile or torch.export."*

## Existing Mechanism

`.scaffold/ml/model_io.py` already wraps all torch serialization
behind a unified API with a priority-ordered fallback chain:

1. `torch.export.export()` (line 198) — preferred, modern path
2. `torch.jit.trace()` (line 219) — legacy fallback
3. `torch.save()` state_dict (line 209) — always-works fallback

The wrapper probes backend availability at import time (lines 46-67)
and auto-selects the best available backend. Production callers go
through `model_io.save_model()` / `model_io.load_model()` and get
`torch.export` when available.

The warnings fire because tests exercise the JIT backend **directly**
to ensure the fallback path works. This is intentional — the tests
validate that the wrapper handles JIT gracefully even on 3.14.

## Shim layer

`.scaffold/ml/export.py` (lines 1-52) provides backwards-compatible
function names (`export_torchscript`, `load_torchscript`, etc.) that
delegate to `model_io.py`. No direct torch calls.

## Resolution Plan

When the session roadmap is complete:

1. **Evaluate `torch.compile` integration** — not yet used anywhere
   in the codebase. Determine if it replaces the JIT trace path for
   inference optimization.
2. **Update tests** — either migrate JIT-specific tests to
   `torch.export`, or add `@pytest.mark.filterwarnings` to
   acknowledge the deprecation explicitly per-test rather than
   globally.
3. **Do not add a blanket `filterwarnings` suppression** — the
   warnings are a useful signal that the JIT path is aging out.
   Suppressing them hides the migration deadline.
