# Frontend V0.1

V0.1 only needs a minimal page later:

- user input
- send button
- final answer
- agent steps showing `think`, `call`, `observe`, and `final`

## Runtime Protocol (V0.2.1)

The UI should not call `run_agent()` directly. Connect to the backend runtime
transport and render events:

```text
WS /api/runtime
```

Recommended client flow:

1. Open a WebSocket to `/api/runtime`.
2. Send `start_run` with `session_id` and `message`.
3. Render incoming `agent_step` events as the loop progresses.
4. When `permission_required` arrives, show an approve/deny UI.
5. Send `permission_decision` with the returned `run_id` and
   `permission_request_id`.
6. Stop on `run_finished`, `run_failed`, or `run_cancelled`.

`POST /api/chat` remains available for simple one-shot requests, but it cannot
pause for user approval. Interactive desktop or web clients should use the
runtime protocol above.

The backend is implemented first so the agent loop is real before UI polish begins.
