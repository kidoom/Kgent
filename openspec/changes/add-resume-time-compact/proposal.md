## Why

Kgent can resume from an existing compact checkpoint, but sessions that were never compacted, were created before checkpoints existed, or accumulated too much context after the latest checkpoint still hydrate into an oversized working state. Resume-time Compact closes that gap by checking hydrated sessions before a new run starts and creating a compact checkpoint when the restored working state is already too large.

This keeps reopen/resume behavior predictable: old sessions can be safely continued without waiting for the first main model call to fail or rely only on run-time AutoCompact.

## What Changes

- Add a resume-time compact check after `hydrate_messages` restores a session into memory and before scheduling a new run.
- Build a request-view estimate from the hydrated `session.messages`, project context, todo reminder, and MicroCompact.
- Trigger the shared compact core with reason `resume_compact` when the hydrated request view exceeds the configured threshold.
- Persist a summary checkpoint with `recent_messages`, then rewrite the in-memory session to `summary boundary + recent`.
- Skip resume-time compact when the session already fits, when compression is disabled, when persistence is disabled, or when there is an active run.
- Treat resume-time compact failures as non-fatal by continuing to the normal run path, where AutoCompact/ReactiveCompact still provide backstops.
- Expose enough warnings or debug metadata to distinguish resume-time compact from auto/reactive/manual compact.

## Capabilities

### New Capabilities

- `resume-time-compact`: Defines proactive compaction of hydrated sessions before a resumed run continues.

### Modified Capabilities

- None.

## Impact

- Affected backend code:
  - `backend/app/api/sessions.py`
  - `backend/app/memory/persistence.py`
  - `backend/app/runtime/context_compression.py`
  - `backend/app/runtime/loop.py` if compact helpers are shared further
  - `backend/app/runtime/todo_state.py` only if todo reminder participation needs helper extraction
- Affected tests:
  - session API resume tests
  - compact core tests
  - hydrate/checkpoint tests
- No public API breaking change is expected.
