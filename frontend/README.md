# Kgent Desktop Client

Vite + React UI in a standalone **Electron window** (not a browser tab).
Connects to the Python WebSocket runtime server.

## Development

**Terminal 1 — backend**

```bash
cd backend
set KGENT_PERMISSION_MODE=interactive
python -m app.transport.ws_server
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

WebSocket URL (`.env.development`):

```text
VITE_WS_URL=ws://127.0.0.1:8765/runtime
```

## Browser mode (optional)

```bash
npm run dev:web
```

Open http://127.0.0.1:5173 in a browser.

## Protocol

See [`backend/app/runtime/protocol.py`](../backend/app/runtime/protocol.py).
