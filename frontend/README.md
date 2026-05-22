# Kgent Desktop Client

Vite + React UI in a standalone **Electron window** (not a browser tab).
Connects to the Python HTTP + SSE runtime server.

## Development

**Terminal 1 — backend**

```bash
cd backend
set KGENT_PERMISSION_MODE=interactive
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or from repo root (reads `.env`, optional TLS):

```bash
python scripts/run_server.py
```

**Terminal 2 — desktop window**

```bash
cd frontend
npm install
npm run desktop:dev
```

If Vite is already running, open the window only:

```bash
npm run desktop
```

## Configuration

API base URL (`.env.development`):

```text
VITE_API_BASE=
```

Leave empty to use same-origin relative paths (`/api/...`) via Vite proxy.

Optional fixed session id:

```text
VITE_SESSION_ID=
```

## Browser mode (optional)

```bash
npm run dev:web
```

Open http://127.0.0.1:5173 in a browser.

## Protocol

See [`backend/app/runtime/protocol.py`](../backend/app/runtime/protocol.py) and [`docs/API.md`](../docs/API.md).
