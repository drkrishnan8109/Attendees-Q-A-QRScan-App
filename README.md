# Live Presentation Q&A

A Streamlit app for collecting audience questions during presentations. The
presenter creates a separate room for each event and displays its QR code. Attendees
join without accounts, submit questions, and like or unlike each question once per
anonymous browser token. Questions always remain in oldest-first order.

## What is included

- Password-protected presenter console
- Reusable presentation rooms with unique audience links and QR codes
- Mobile-friendly, password-free audience view
- Plain-text questions limited to 280 characters
- Oldest-first live feeds that refresh every two seconds
- Reversible one-like-per-browser-token reactions
- Local SQLite persistence
- Complete JSON backup/restore and readable, formula-safe CSV export
- Input validation, parameterized SQL, bounded uploads, and temporary login lockouts

## Run locally

Python 3.12 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements-dev.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run streamlit_app.py
```

Edit `.streamlit/secrets.toml` before signing in:

```toml
presenter_password = "use-a-long-random-password-here"
```

The local database is created at `.qa_data/questions.sqlite3`. Both it and the real
secrets file are ignored by Git.

### Let phones reach a locally running app

If the laptop and phones share a Wi-Fi network, start Streamlit on all interfaces and
configure the QR base URL with the laptop's LAN address:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

```toml
app_base_url = "http://192.168.1.25:8501/"
```

Replace the example address with the laptop's current LAN address. Some corporate or
guest networks block communication between devices; Community Cloud avoids that
network limitation.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from the
   repository and choose `streamlit_app.py` as the entry point.
3. In the app's advanced settings, add this secret:

   ```toml
   presenter_password = "use-a-long-random-password-here"
   ```

4. Optionally add the final app URL. The app normally detects it automatically:

   ```toml
   app_base_url = "https://your-app-name.streamlit.app/"
   ```

5. Open the base URL, sign in, create a room, and verify the generated audience link
   before the presentation begins.

The audience QR URL contains `?room=<room-id>`. Each audience browser receives a
random `viewer` query parameter on first load so it can toggle its own reaction.

## Persistence and backups

SQLite works normally on a laptop. On Community Cloud, local filesystem persistence
is best-effort: a reboot, redeploy, or platform reset may remove the database.

After each presentation, open the **Backups** tab and download:

- **Restorable JSON** to preserve rooms, questions, order, and reaction state.
- **Readable CSV** for analysis or sharing. Spreadsheet formula prefixes are
  neutralized during export.

JSON restore is deliberately available only when the app database is empty. This
prevents an upload from silently overwriting or merging current questions. If you
need to restore locally while a database exists, stop the app and move the current
database file to a safe backup location first; then restart and upload the JSON.

## Use during a presentation

1. Open the app's base URL and sign in as presenter.
2. Create or select a presentation room.
3. Put the displayed QR code on a slide.
4. Keep the **Live room** tab open while presenting.
5. Download the JSON backup when the session ends.

Attendees only need the QR link. They never see room creation or backup controls.

## Verify changes

```bash
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python -m compileall -q qa_app streamlit_app.py tests
```

The tests cover validation, chronological ordering, room isolation, reaction
toggling, JSON round-trips, safe CSV export, presenter authentication, room creation,
and the complete audience submit/react flow through Streamlit's native app harness.

## Intentional MVP limits

- Browser-token reaction enforcement is a convenience, not strong anti-abuse
  identity. Clearing or replacing the URL token permits another vote.
- There are no attendee accounts, moderation controls, question deletion, or room
  deletion.
- Community Cloud SQLite is not guaranteed durable; use the JSON backup.
- Restore does not merge datasets. It only restores into an empty database.
