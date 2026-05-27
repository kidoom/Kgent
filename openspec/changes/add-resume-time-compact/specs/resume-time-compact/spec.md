## ADDED Requirements

### Requirement: Resume-time compact checks hydrated sessions

The system SHALL evaluate a hydrated session before a resumed run starts and determine whether the restored working state should be compacted.

#### Scenario: Hydrated session exceeds threshold

- **WHEN** a session is hydrated from transcript and its rebuilt request view exceeds the configured compact threshold
- **THEN** the system triggers Resume-time Compact before scheduling the resumed run

#### Scenario: Hydrated session is below threshold

- **WHEN** a session is hydrated from transcript and its rebuilt request view is below the configured compact threshold
- **THEN** the system does not compact the session during resume

### Requirement: Resume-time compact uses the active request shape

The system SHALL estimate resume-time compact eligibility using request messages built from hydrated `session.messages`, runtime context, todo reminder, and request-view MicroCompact when enabled.

#### Scenario: Todo reminder is present

- **WHEN** todo state exists for the session during resume
- **THEN** the resume-time compact estimate includes the todo reminder in the rebuilt request view

#### Scenario: MicroCompact is enabled

- **WHEN** MicroCompact is enabled during resume-time evaluation
- **THEN** the system estimates the micro-compacted request view instead of the raw request view

### Requirement: Resume-time compact writes a checkpoint before rewriting memory

The system SHALL persist a summary checkpoint with reason `resume_compact` and saved `recent_messages` before replacing hydrated `session.messages`.

#### Scenario: Resume compact succeeds

- **WHEN** Resume-time Compact successfully generates a summary
- **THEN** the transcript contains a summary entry with reason `resume_compact`, summary text, before/after message counts, and `recent_messages`
- **AND** the in-memory session is rewritten to `summary boundary + recent messages`

#### Scenario: Summary persistence fails

- **WHEN** the summary checkpoint cannot be persisted
- **THEN** the system does not rewrite the in-memory session during Resume-time Compact

### Requirement: Resume-time compact is non-fatal

The system SHALL continue the normal run path when Resume-time Compact fails.

#### Scenario: Summarizer fails during resume

- **WHEN** Resume-time Compact fails because the internal summarizer errors or returns an empty summary
- **THEN** the API still schedules the resumed run and leaves AutoCompact or ReactiveCompact to handle later compaction

### Requirement: Resume-time compact respects compression settings

The system SHALL skip Resume-time Compact when context compression or auto compaction is disabled.

#### Scenario: Context compression disabled

- **WHEN** `context_compression_enabled` is false
- **THEN** Resume-time Compact does not run

#### Scenario: Auto compact disabled

- **WHEN** `auto_compact_enabled` is false
- **THEN** Resume-time Compact does not run

### Requirement: Resume-time compact avoids active-run races

The system SHALL NOT compact a session during resume while that session already has an active run.

#### Scenario: Session has active run

- **WHEN** a session already has an active run
- **THEN** Resume-time Compact is skipped and the existing conflict handling remains responsible for the response
