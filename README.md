# Kgent

Kgent V0.1 is a minimal FastAPI agent runtime built from a Claude Code-style agent loop.

The first version intentionally stays small:

```text
user input -> model -> tool_use -> runtime -> tool_result -> model -> final answer
```

## Run Backend

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --app-dir backend --reload
```

Then send a request:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"帮我算一下 12 * 8 + 6\"}"
```

## V0.1 Design

See [DEV_SPEC.md](DEV_SPEC.md).

## Model Client

By default, Kgent uses a deterministic local model client so the agent loop can be tested without an API key. Set `KGENT_MODEL_CLIENT=openai` and `OPENAI_API_KEY` later when we add the real provider path.
