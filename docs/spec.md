# Spec: Live Presentation Q&A

## Objective

Build a lightweight Streamlit application for live presentation Q&A. A presenter
creates reusable rooms and shares a room-specific QR code. Anonymous attendees can
submit plain-text questions and like or unlike each question once per browser token.
The presenter sees the same questions live, always ordered from oldest to newest,
and can revisit previous rooms.

The application targets a free Streamlit Community Cloud deployment. SQLite is the
default store and is explicitly best-effort in that environment. Full JSON backups
and human-readable CSV exports provide the durable handoff path without requiring a
hosted database.

## Tech Stack

- Python 3.12+
- Streamlit 1.60.0
- Python standard-library `sqlite3`
- `qrcode` 8.2 with Pillow image support
- `unittest` for automated tests
- Ruff 0.16.0 for linting and formatting checks

## Commands

- Install: `python3 -m pip install -r requirements-dev.txt`
- Run: `streamlit run streamlit_app.py`
- Test: `python3 -m unittest discover -s tests -v`
- Lint: `ruff check .`
- Format check: `ruff format --check .`
- Compile check: `python3 -m compileall -q qa_app streamlit_app.py tests`

## Project Structure

```text
streamlit_app.py          Streamlit routing and presentation
qa_app/models.py          Typed application records
qa_app/validation.py      Input-boundary validation and text escaping
qa_app/storage.py         SQLite schema, queries, reactions, and backups
tests/                    Unit and SQLite integration tests
docs/                     Product specification
tasks/                    Implementation plan and checklist
.streamlit/               Safe theme configuration and secrets example
```

## Code Style

Use type hints, descriptive snake-case names, short focused functions, parameterized
SQL, and UTC ISO-8601 timestamps.

```python
def create_question(self, room_id: str, body: str) -> Question:
    clean_body = validate_question(body)
    question = Question.create(room_id=room_id, body=clean_body)
    self._insert_question(question)
    return question
```

## Testing Strategy

- Pure unit tests cover title/question validation, URL-token validation, and Markdown
  escaping.
- SQLite integration tests use a temporary database and cover schema initialization,
  chronological ordering, room isolation, reversible single-voter reactions, and
  backup export/import.
- Streamlit startup is verified headlessly in addition to compile and lint checks.
- Runtime UI verification covers audience and presenter routes at desktop and narrow
  viewport widths where local browser tooling is available.

## Boundaries

- Always: validate input, parameterize SQL, compare the presenter secret in constant
  time, keep attendee content plain text, and keep questions ordered oldest first.
- Ask first: add moderation/deletion, attendee accounts, external services, or change
  the storage contract.
- Never: commit secrets, promise durable Community Cloud filesystem storage, render
  attendee input as raw HTML, or treat browser tokens as strong authentication.

## Success Criteria

1. The presenter can authenticate and create multiple named rooms.
2. Every room has a distinct public identifier, audience link, and QR code.
3. An attendee can open a room without an account and submit a 1-280 character
   plain-text question.
4. Questions remain isolated by room and render oldest first with deterministic ties.
5. A browser token can like and unlike each question; duplicate likes are impossible.
6. Presenter and audience question lists refresh automatically during a live session.
7. Rooms and questions survive ordinary app reruns in SQLite.
8. The presenter can download a restorable JSON backup and a readable CSV export,
   and can import a valid JSON backup.
9. Missing configuration, empty rooms, invalid links, and invalid uploads show clear
   user-facing states without leaking internal errors.

## Open Questions

None for the confirmed MVP. Strong identity, moderation, and guaranteed hosted
persistence are explicitly deferred.
