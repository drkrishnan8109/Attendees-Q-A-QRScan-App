# Live Presentation Q&A Tasks

## Task 1: Project and validation foundation

**Acceptance criteria:**
- [x] Runtime and development dependencies are pinned.
- [x] Secrets and generated data are ignored.
- [x] Room titles, questions, room IDs, and viewer IDs are validated.

**Verification:** `python3 -m unittest tests.test_validation -v`

**Dependencies:** None

**Files:** configuration, `qa_app/validation.py`, `tests/test_validation.py`

## Task 2: Rooms and chronological questions

**Acceptance criteria:**
- [x] Multiple rooms persist with distinct opaque IDs.
- [x] Questions are isolated by room.
- [x] Questions return oldest first with deterministic tie ordering.

**Verification:** `python3 -m unittest tests.test_storage.StorageQuestionTests -v`

**Dependencies:** Task 1

**Files:** `qa_app/models.py`, `qa_app/storage.py`, `tests/test_storage.py`

## Task 3: Reactions and backups

**Acceptance criteria:**
- [x] A voter toggles each question between liked and unliked.
- [x] The database cannot store duplicate likes.
- [x] JSON export/import round-trips rooms, questions, and reactions.

**Verification:** `python3 -m unittest tests.test_storage -v`

**Dependencies:** Task 2

**Files:** `qa_app/storage.py`, `tests/test_storage.py`

## Task 4: Audience flow

**Acceptance criteria:**
- [x] Valid QR links open a password-free audience room.
- [x] Questions can be submitted and reactions toggled.
- [x] The question list refreshes live and remains chronological.

**Verification:** headless Streamlit startup and manual narrow-viewport check

**Dependencies:** Tasks 2-3

**Files:** `streamlit_app.py`

## Task 5: Presenter flow and QR

**Acceptance criteria:**
- [x] Invalid secrets do not unlock presenter controls.
- [x] The presenter can create/select rooms and see live questions.
- [x] Each selected room displays a unique working QR code.

**Verification:** headless Streamlit startup and manual presenter-flow check

**Dependencies:** Tasks 2-4

**Files:** `streamlit_app.py`, `.streamlit/config.toml`

## Task 6: Backup controls and documentation

**Acceptance criteria:**
- [x] Presenter can download full JSON and readable CSV.
- [x] Presenter can import a bounded valid JSON backup.
- [x] Local and Community Cloud setup are documented without committed secrets.

**Verification:** full tests plus README setup walkthrough

**Dependencies:** Tasks 3 and 5

**Files:** `streamlit_app.py`, `README.md`, secrets example

## Task 7: Quality gate

**Acceptance criteria:**
- [x] Tests, lint, formatting, compilation, and startup checks pass.
- [x] Security and five-axis review have no unresolved required findings.

**Verification:** commands in `docs/spec.md`

**Dependencies:** All prior tasks

**Files:** only files required by review findings
