# Live Presentation Q&A Tasks

## Task 1: Project and validation foundation

**Acceptance criteria:**
- [ ] Runtime and development dependencies are pinned.
- [ ] Secrets and generated data are ignored.
- [ ] Room titles, questions, room IDs, and viewer IDs are validated.

**Verification:** `python3 -m unittest tests.test_validation -v`

**Dependencies:** None

**Files:** configuration, `qa_app/validation.py`, `tests/test_validation.py`

## Task 2: Rooms and chronological questions

**Acceptance criteria:**
- [ ] Multiple rooms persist with distinct opaque IDs.
- [ ] Questions are isolated by room.
- [ ] Questions return oldest first with deterministic tie ordering.

**Verification:** `python3 -m unittest tests.test_storage.StorageQuestionTests -v`

**Dependencies:** Task 1

**Files:** `qa_app/models.py`, `qa_app/storage.py`, `tests/test_storage.py`

## Task 3: Reactions and backups

**Acceptance criteria:**
- [ ] A voter toggles each question between liked and unliked.
- [ ] The database cannot store duplicate likes.
- [ ] JSON export/import round-trips rooms, questions, and reactions.

**Verification:** `python3 -m unittest tests.test_storage -v`

**Dependencies:** Task 2

**Files:** `qa_app/storage.py`, `tests/test_storage.py`

## Task 4: Audience flow

**Acceptance criteria:**
- [ ] Valid QR links open a password-free audience room.
- [ ] Questions can be submitted and reactions toggled.
- [ ] The question list refreshes live and remains chronological.

**Verification:** headless Streamlit startup and manual narrow-viewport check

**Dependencies:** Tasks 2-3

**Files:** `streamlit_app.py`

## Task 5: Presenter flow and QR

**Acceptance criteria:**
- [ ] Invalid secrets do not unlock presenter controls.
- [ ] The presenter can create/select rooms and see live questions.
- [ ] Each selected room displays a unique working QR code.

**Verification:** headless Streamlit startup and manual presenter-flow check

**Dependencies:** Tasks 2-4

**Files:** `streamlit_app.py`, `.streamlit/config.toml`

## Task 6: Backup controls and documentation

**Acceptance criteria:**
- [ ] Presenter can download full JSON and readable CSV.
- [ ] Presenter can import a bounded valid JSON backup.
- [ ] Local and Community Cloud setup are documented without committed secrets.

**Verification:** full tests plus README setup walkthrough

**Dependencies:** Tasks 3 and 5

**Files:** `streamlit_app.py`, `README.md`, secrets example

## Task 7: Quality gate

**Acceptance criteria:**
- [ ] Tests, lint, formatting, compilation, and startup checks pass.
- [ ] Security and five-axis review have no unresolved required findings.

**Verification:** commands in `docs/spec.md`

**Dependencies:** All prior tasks

**Files:** only files required by review findings
