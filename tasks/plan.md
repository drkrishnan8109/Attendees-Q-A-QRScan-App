# Implementation Plan: Live Presentation Q&A

## Overview

Deliver the app in small vertical slices: establish the tested SQLite contract,
prove room/question/reaction behavior, then layer the two Streamlit views and backup
workflow on top. The UI remains a single Streamlit entry point; application logic is
kept independently testable.

## Architecture Decisions

- Use one SQLite connection per operation with WAL mode, foreign keys, a busy timeout,
  and transactional vote toggles for safe concurrent Streamlit sessions.
- Use opaque URL-safe room IDs and anonymous viewer IDs. Viewer IDs are soft browser
  state carried in audience URLs and are not authentication.
- Keep input validation and persistence out of Streamlit widgets so core behavior is
  testable without a browser.
- Use JSON for complete restore and CSV for convenient reading. Imports are bounded,
  schema-validated, and merged by opaque stable identifiers.
- Use `st.fragment(run_every="2s")` for live lists instead of another service.

## Task List

### Phase 1: Foundation

- [x] Task 1: Add project configuration, documentation, and validation tests.
- [x] Task 2: Implement room and question persistence with chronological queries.
- [x] Task 3: Implement transactional reaction toggling and backup round-tripping.

### Checkpoint: Foundation

- [x] Unit and SQLite integration tests pass.
- [x] Schema and input boundaries match the approved specification.

### Phase 2: Core User Flows

- [x] Task 4: Build anonymous audience submission, live question list, and reactions.
- [x] Task 5: Build protected presenter room creation, room selection, live view, and QR.
- [x] Task 6: Add JSON backup import and JSON/CSV downloads.

### Checkpoint: Core Flows

- [x] Audience URL works without authentication.
- [x] Presenter actions require the configured secret.
- [x] Two browser sessions share persisted state and live-refresh independently.

### Phase 3: Polish and Verification

- [x] Task 7: Add responsive styling, empty/error states, and deployment instructions.
- [x] Task 8: Run lint, format, compile, tests, startup, security, and five-axis review.

### Checkpoint: Complete

- [x] All success criteria pass.
- [x] No secret or generated database is tracked.
- [x] The app is ready for a Community Cloud deployment.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Community Cloud deletes SQLite | High | Honest warning plus restorable JSON and readable CSV exports |
| Concurrent attendees lock SQLite | Medium | Short connections, WAL, busy timeout, indexed queries |
| Repeat votes by token reset | Low | Document soft enforcement; strong identity is out of scope |
| Presenter URL is wrong in QR | Medium | Optional configured base URL with current URL fallback |
| Malicious or huge input | Medium | Strict lengths, control-character checks, parameterized SQL, bounded import |

## Open Questions

None.
