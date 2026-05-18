#!/usr/bin/env python3
"""Bootstrap a DEV_SPEC.md from the methodology template.

Usage:
    python init_spec.py <project_name> [--path <output_dir>]

Example:
    python init_spec.py my-web-api --path ./specs
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import date


TEMPLATE = """\
# DEV_SPEC: {project_name}

> Version: 1.0 — {date}

---

## 1. 项目概述

### 1.1 背景

`{project_name}` 是一个 `{{一句话描述}}`。
本项目通过 `{{方案概述}}` 解决 `{{问题陈述}}`。

### 1.2 设计理念

> **核心定位：`{{核心理念标语}}`**

`{{2-3 段话解释项目存在的理由}}`

#### 1）`{{设计原则 1}}`（`{{标语}}`）

`{{解释 + 架构体现}}`

#### 2）`{{设计原则 2}}`（`{{标语}}`）

`{{解释}}`

#### 3）`{{设计原则 3}}`（`{{标语}}`）

`{{解释}}`

### 1.3 目标受众

| 受众 | 获得什么 | 使用方式 |
|------|---------|---------|
| `{{受众}}` | `{{价值}}` | `{{模式}}` |

### 1.4 范围边界

**范围内：**
- `{{特性}}`

**明确排除：**
- `{{特性}}` — `{{原因}}`

---

## 2. 核心特性

### 2.1 `{{特性名 1}}`

- **问题陈述**：`{{}}`
- **方案路径**：`{{}}`
- **设计亮点**：
    - `{{}}`
- **权衡分析**：

| 维度 | 选项 A | 选项 B | 决策 |
|------|--------|--------|------|
| `{{维度}}` | `{{分析}}` | `{{分析}}` | `{{选择}}` |

- **当前状态**：`{{}}`
- **扩展点**：`{{}}`

---

## 3. 技术选型

### 3.1 `{{子系统 1}}`

#### 3.1.1 `{{组件}}`

**接口定义：**

```python
class Base{{Component}}:
    def {{method}}(self, {{params}}) -> {{return_type}}:
        raise NotImplementedError
```

**配置：**
```yaml
{{subsystem}}:
  {{component}}:
    backend: {{default}}  # {{opt1}} | {{opt2}} | {{opt3}}
```

**工厂模式：**
```python
class {{Component}}Factory:
    @staticmethod
    def create(settings) -> Base{{Component}}:
        backend = settings.{{sub}}.{{comp}}.backend
        if backend == "{{opt1}}":
            return {{Opt1Impl}}()
        elif backend == "{{opt2}}":
            return {{Opt2Impl}}()
        else:
            raise ValueError(f"Unknown backend: {{backend}}")
```

**降级策略**：`{{失败时怎么办}}`

---

## 4. 测试方案

### 4.1 TDD 哲学

早测试、常测试。测试即文档。快速反馈。分层金字塔。

```
        /\\
       /E2E\\
      /------\\
     /Integration\\
    /------------\\
   /  Unit Tests  \\
  /________________\\
```

### 4.2 测试分层

#### 单元测试

| 模块 | 测试重点 | 典型用例 |
|------|---------|---------|
| `{{模块}}` | `{{验证什么}}` | `{{场景}}` |

#### 集成测试

| 场景 | 验证要点 | 策略 |
|------|---------|------|
| `{{场景}}` | `{{验证}}` | `{{方法}}` |

#### E2E 测试

**场景 1：`{{名称}}`**
- 目标：`{{}}`
- 步骤：`{{}}`
- 验证：`{{}}`

### 4.3 质量指标

| 类别 | 指标 | 目标 |
|------|------|------|
| 单元测试 | 覆盖率 | >= 80% |
| 集成测试 | 关键路径 | 100% |

### 4.4 黄金测试集

```json
[
  {{
    "input": "{{test_input}}",
    "expected_output": "{{expected}}",
    "metadata": {{"difficulty": "easy|medium|hard", "tags": []}}
  }}
]
```

---

## 5. 系统架构与模块设计

### 5.1 架构图

```
┌─────────────────────────┐
│      {{接口层}}          │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│      {{核心逻辑层}}      │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│      {{抽象层}}          │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│      {{存储层}}          │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│      {{可观测性层}}      │
└─────────────────────────┘
```

### 5.2 目录结构

```
{project_name}/
├── config/
│   ├── settings.yaml
│   └── prompts/
├── src/
│   ├── core/
│   │   ├── settings.py
│   │   └── types.py
│   ├── libs/
│   │   └── {{component}}/
│   │       ├── base_{{component}}.py
│   │       ├── {{component}}_factory.py
│   │       └── {{impl}}.py
│   └── observability/
│       ├── logger.py
│       └── trace_context.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── data/
├── logs/
├── scripts/
├── main.py
├── pyproject.toml
└── README.md
```

### 5.3 数据流

```
{{输入}} → {{阶段1}} → {{阶段2}} → {{阶段3}} → {{输出}}
```

### 5.4 配置驱动

```yaml
# config/settings.yaml
{{subsystem}}:
  {{component}}:
    backend: {{default}}

observability:
  log_level: INFO
```

---

## 6. 项目排期

> **原则**：一小时一增量 | 先打通主闭环 | 外部依赖可 Mock

### 阶段总览

| 阶段 | 目的 |
|------|------|
| A | 工程骨架与测试基座 |
| B | 可插拔抽象层 |
| C | 主处理流水线 |
| D | 请求处理流水线 |
| E | 接口/API 层 |
| F | 可观测性基础设施 |
| G | 管理 Dashboard |
| H | 评估体系 |
| I | 端到端验收与文档 |

### 进度跟踪

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| A1 | 初始化目录树 | [ ] | | |
| A2 | 引入测试框架 | [ ] | | |
| A3 | 配置加载与校验 | [ ] | | |

### 详细任务

### A1：初始化目录树与最小可运行入口
- **目标**：创建目录骨架与空模块文件
- **修改文件**：`main.py`, `pyproject.toml`, `src/**/__init__.py`
- **实现类/函数**：无（仅骨架）
- **验收标准**：目录结构与 5.2 一致，可 import
- **测试方法**：`python -m compileall src`

### A2：引入测试框架
- **目标**：建立 pytest 配置与测试目录
- **修改文件**：`pyproject.toml`, `tests/unit/test_smoke.py`
- **实现类/函数**：无
- **验收标准**：`pytest -q` 通过
- **测试方法**：`pytest -q tests/unit/test_smoke.py`

### A3：配置加载与校验
- **目标**：实现 settings.yaml 读取与校验
- **修改文件**：`src/core/settings.py`, `config/settings.yaml`
- **实现类/函数**：`Settings`, `load_settings()`, `validate_settings()`
- **验收标准**：启动时校验必填字段，缺失时给出可读错误
- **测试方法**：`pytest -q tests/unit/test_config.py`
"""


def main():
    parser = argparse.ArgumentParser(description="Bootstrap a DEV_SPEC.md")
    parser.add_argument("project_name", help="Project name")
    parser.add_argument("--path", default=".", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "DEV_SPEC.md"

    if output_path.exists():
        print(f"WARNING: {output_path} already exists. Skipping.")
        sys.exit(0)

    content = TEMPLATE.format(
        project_name=args.project_name,
        date=date.today().isoformat(),
    )
    output_path.write_text(content, encoding="utf-8")
    print(f"Created {output_path}")


if __name__ == "__main__":
    main()
