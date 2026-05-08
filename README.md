# Kagent

Pluggable AI Agent Framework — build agents with swappable LLMs and tools.

## Install

```bash
pip install -e ".[dev]"
```

## Quickstart

```python
from kagent import SimpleAgent, AgentLLM, Config

llm = AgentLLM(config=Config(api_key="sk-xxx"))
agent = SimpleAgent(name="demo", llm=llm)
print(agent.run("Hello!"))
```

## v0.1 Scope

- **Agent 范式**: SimpleAgent (prompt-based tool calling), ReActAgent (Thought/Action/Observation)
- **LLM 可插拔**: OpenAI-compatible providers, lazy-load via config
- **工具可插拔**: ToolRegistry with Calculator + Search built-in
- **配置驱动**: `.env` based config via `Config.from_env()`

See [DEV_SPEC.md](DEV_SPEC.md) for full specification.
