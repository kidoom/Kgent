## 1. Resume Evaluation Helper

- [x] 1.1 Add a helper that builds the same request view used by a resumed run from hydrated `session.messages`, project context, todo reminder, and MicroCompact settings.
- [x] 1.2 Add a helper that decides whether Resume-time Compact should run using `CompressionConfig` and `should_auto_compact`.
- [x] 1.3 Ensure the helper skips when `context_compression_enabled` or `auto_compact_enabled` is false.

## 2. Resume Compact Execution

- [x] 2.1 Wire Resume-time Compact into the session message API after hydrate/todo hydration and before scheduling the background run.
- [x] 2.2 Ensure the active-run conflict path prevents resume compact from running during an existing run.
- [x] 2.3 Reuse `execute_compact` with reason `resume_compact`, configured recent-message retention, and summary persistence.
- [x] 2.4 Persist the summary checkpoint before rewriting memory and keep the hydrated session unchanged when persistence fails.
- [x] 2.5 Treat Resume-time Compact failures as non-fatal and continue scheduling the normal run.

## 3. Configuration And Consistency

- [x] 3.1 Reuse the same `CompressionConfig` construction for Resume-time Compact and the scheduled run.
- [x] 3.2 Include todo reminder state in resume-time request estimation when todo state exists.
- [x] 3.3 Apply MicroCompact settings during resume-time estimation when enabled.
- [x] 3.4 Add debug or warning visibility for skipped, successful, and failed resume-time compact decisions.

## 4. Tests

- [x] 4.1 Add a test that an oversized hydrated session triggers `resume_compact` and writes a summary entry with `recent_messages`.
- [x] 4.2 Add a test that a below-threshold hydrated session skips Resume-time Compact.
- [x] 4.3 Add tests that disabled context compression or disabled auto compact skip Resume-time Compact.
- [x] 4.4 Add a test that resume compact failure does not block scheduling the run and does not rewrite session messages.
- [x] 4.5 Add a test that active-run conflict handling prevents resume compact work.
- [x] 4.6 Run focused API session, compact core, and runtime loop tests.
