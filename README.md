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

## Quick start

Python 3.12 is recommended. From a fresh checkout:

```bash
git clone https://github.com/drkrishnan8109/Attendees-Q-A-QRScan-App.git
cd Attendees-Q-A-QRScan-App
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and replace the example presenter password. It must
contain at least 12 characters:

```toml
presenter_password = "use-a-long-random-password-here"
```

Start the app:

```bash
python -m streamlit run streamlit_app.py
```

Open <http://127.0.0.1:8501>. Stop the server with `Ctrl+C`. If port 8501 is already
in use, choose another port:

```bash
python -m streamlit run streamlit_app.py --server.port 8502
```

The SQLite database is created at `.qa_data/questions.sqlite3`. The database, virtual
environment, Python caches, and real secrets file are ignored by Git.

### Development setup and checks

Install the development dependencies instead of the runtime-only set:

```bash
python -m pip install -r requirements-dev.txt
```

Run the complete local quality gate:

```bash
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python -m compileall -q qa_app streamlit_app.py tests
```

### Let phones reach a locally running app

If the laptop and phones share a Wi-Fi network, first find the laptop's LAN address.
On macOS, Wi-Fi commonly uses `en0`:

```bash
ipconfig getifaddr en0
```

Then start Streamlit on all interfaces:

```bash
python -m streamlit run streamlit_app.py --server.address 0.0.0.0
```

Add the same address and Streamlit port to `.streamlit/secrets.toml` so generated QR
codes point to an address attendees can reach:

```toml
app_base_url = "http://192.168.1.25:8501/"
```

Replace the example address with the value reported on your laptop. Test the link on
a phone before presenting. macOS may ask whether Python can accept incoming network
connections. Some corporate or guest networks isolate devices from one another; use
a hosted deployment when that happens.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub. Do not commit `.streamlit/secrets.toml` or
   `.qa_data/`.
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

The tests cover packaging, validation, chronological ordering, room isolation, reaction
toggling, JSON round-trips, safe CSV export, presenter authentication, room creation,
and the complete audience submit/react flow through Streamlit's native app harness.

## Troubleshooting

- **Presenter password is not configured:** create `.streamlit/secrets.toml` from the
  included example and use a password of at least 12 characters.
- **The QR code opens the wrong address:** set `app_base_url` to the exact URL that
  attendee devices use, including a non-default port.
- **A phone cannot connect:** confirm both devices use the same network, use the
  laptop's LAN address rather than `localhost`, and allow incoming connections in the
  firewall.
- **Port 8501 is busy:** pass `--server.port 8502` and use that same port in
  `app_base_url`.
- **Community Cloud lost questions after a restart:** restore the most recent JSON
  backup; local SQLite storage on Community Cloud is not guaranteed durable.

## Intentional MVP limits

- Browser-token reaction enforcement is a convenience, not strong anti-abuse
  identity. Clearing or replacing the URL token permits another vote.
- There are no attendee accounts, moderation controls, question deletion, or room
  deletion.
- Community Cloud SQLite is not guaranteed durable; use the JSON backup.
- Restore does not merge datasets. It only restores into an empty database.
