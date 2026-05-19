## 4. 模块划分

建议目录：

```text
mini-agent/
  backend/
    app/
      main.py
      api/
        chat.py
      agent/
        loop.py
        messages.py
        model_client.py
        prompts.py
      tools/
        base.py
        registry.py
        calculator.py
        read_file.py
        list_files.py
      core/
        config.py
    pyproject.toml
  frontend/
    README.md
```

模块职责：

| 模块 | 职责 |
| --- | --- |
| `main.py` | FastAPI 应用入口 |
| `api/chat.py` | HTTP 接口，接收前端请求 |
| `agent/loop.py` | 控制 model-tool-model 循环 |
| `agent/model_client.py` | 封装模型请求 |
| `agent/messages.py` | 定义 message / tool_use / tool_result 数据结构 |
| `agent/prompts.py` | 存放 system prompt |
| `tools/base.py` | 定义 Tool 基类 / 协议 |
| `tools/registry.py` | 注册工具并提供 `find_tool_by_name()` |
| `tools/*.py` | 具体工具实现 |
| `core/config.py` | 环境变量和运行配置 |
