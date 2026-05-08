# Kagent

Pluggable AI Agent framework for building tool-using LLM agents.

## Install

```bash
pip install -e ".[dev]"
```

## Quickstart

```python
from kagent.core import AgentLLM, Config

config = Config.from_env()
llm = AgentLLM(config=config)

response = llm.invoke([{"role": "user", "content": "Hello, Kagent!"}])
print(response.content)
```

## Current Scope

- Stage A complete: config, LLM provider layer, tool system, built-in tools
- Stage B in progress: agent paradigms (`Agent`, `Message`, `SimpleAgent`, `ReActAgent`)
- Full plan and milestones: see `DEV_SPEC.md`
