## 2. 非目标

V0.1 暂不实现：

- 工具并发调度
- 完整权限审批系统（V0.2 已实现 CLI 交互 + risk_based 策略，见 §18）
- 上下文压缩
- 长期记忆
- MCP
- 动态工具加载
- 流式输出
- 多模型 provider 泛化（生产仅 `openai` 兼容 client，如 DeepSeek；pytest 用 `tests/fake_model.py`）
- 复杂桌面/Electron 打包（**Vite + React Web 客户端已实现**，见 §18.6；与 Cursor/CC 级产品 UI 仍非目标）
- 数据库存储 / session 持久化
- 用户登录系统
- 自动任务规划

其余能力见 §20 路线图，按版本逐步加入。
