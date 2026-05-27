## Context

Kgent currently has two resume-related behaviors. First, `hydrate_messages` can restore a session from transcript into `summary boundary + recent_messages + later messages` when a previous compact checkpoint exists. Second, the normal run loop can AutoCompact before the main model call if the request view is too large.

Resume-time Compact is a middle layer between those behaviors. It runs after a session is hydrated into memory, but before the resumed user run is scheduled. Its job is to create a compact checkpoint for oversized hydrated sessions that do not already have a sufficiently small working state.

## Goals / Non-Goals

**Goals:**

- Detect oversized hydrated sessions before scheduling a resumed run.
- Reuse the same compact core used by AutoCompact, ReactiveCompact, and ManualCompact.
- Respect existing compression configuration and project root.
- Persist a `summary` transcript entry with `recent_messages` before rewriting memory.
- Keep failures non-fatal so users can still proceed through the normal AutoCompact/ReactiveCompact path.
- Avoid compacting sessions that are already active or already below threshold.

**Non-Goals:**

- Replace hydrate checkpoint restoration.
- Compact every session list/read operation.
- Delete or rewrite old transcript entries.
- Introduce a new summarizer model or provider.
- Guarantee that resume-time compact runs without a model client; it requires the same model client used for normal runs.

## Decisions

### Run resume-time compact after hydrate and before run scheduling

The session API should call a helper after `_hydrate_session_if_needed` and todo-state hydration, before `start_run_if_idle` or immediately after idle is confirmed but before scheduling the background run.

Rationale: the session must be in memory before it can be measured and compacted, and compact should not race with an active run.

Alternative considered: run inside `hydrate_messages`. This was rejected because hydrate is a persistence-layer operation and should not call the model.

### Measure the same request view the run will use

The resume check should build request messages from hydrated `session.messages`, project context, and todo reminder, then apply MicroCompact if enabled before estimating tokens.

Rationale: measuring only raw `session.messages` can overestimate or underestimate the real model request. Resume-time Compact should use the same shape as run-time AutoCompact.

Alternative considered: estimate transcript entry sizes directly. This does not account for context builder output or request-view MicroCompact.

### Reuse `execute_compact` with reason `resume_compact`

Resume-time Compact should call the shared compact core with the same `COMPACT_SYSTEM_PROMPT`, `compact_user_prompt`, recent-message retention, and summary persistence behavior.

Rationale: separate compact implementations drift quickly. The shared core already handles summarization, retry, persistence-before-rewrite, and request rebuild.

Alternative considered: delegate to AutoCompact inside the first loop turn. That works later, but does not produce an explicit resume checkpoint before the run begins.

### Treat failures as non-fatal

If resume-time compact fails, the API should proceed with scheduling the normal run. AutoCompact and ReactiveCompact remain backstops.

Rationale: resume compact is an optimization and checkpoint hygiene layer. It should not prevent the user from continuing a session because the summarizer or transcript append failed.

Alternative considered: fail the send-message request. This is stricter but creates unnecessary user-visible failures for a recoverable condition.

## Risks / Trade-offs

- [Risk] Resume-time Compact adds latency before a resumed run starts -> Mitigation: run it only when the hydrated request exceeds threshold.
- [Risk] Compact could duplicate work with AutoCompact -> Mitigation: after successful resume compact, the rewritten session should be below threshold, so AutoCompact should usually skip.
- [Risk] Compact can fail due to transcript size or model errors -> Mitigation: do not rewrite memory unless persistence succeeds; proceed to the normal run path on failure.
- [Risk] Triggering before idle check could race with active runs -> Mitigation: ensure no active run is in progress before executing resume compact.
- [Risk] Manual/auto/resume compact settings diverge -> Mitigation: construct one `CompressionConfig` from `Settings` and reuse it for resume and scheduled runs.
