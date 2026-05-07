## 7. Axioms（内嵌原则）

1. **Spec before implementation** — 接口 + 契约 + 验收标准先于代码定义
2. **One hour, one verifiable increment** — 每个任务 ~1h，有可测试的输出
3. **Test-first, always** — 先写测试方法，再写代码
4. **Interfaces before implementations** — 抽象基类 + 工厂先于具体实现
5. **Configuration drives behavior** — 单一配置源，切换零代码改动
6. **Fail fast, degrade gracefully** — 启动时校验，运行时降级；工具失败返回用户可读错误，不中断 Agent 循环
7. **Observability is not optional** — 每次 run() 生成 trace_id + 结构日志 + Token 用量统计
8. **SPEC is a living document** — 每完成一个任务更新进度表
