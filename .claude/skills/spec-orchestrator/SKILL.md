---
name: spec-orchestrator
description: "Spec-driven project orchestration methodology. Generates a complete DEV_SPEC.md for any software project by guiding through 6 structured sections (Overview, Features, Tech Decisions, Testing, Architecture, Schedule) with phased task breakdown. Use when user says '写spec', '编排spec', '生成开发规范', 'create spec', 'spec methodology', '项目排期', '任务编排', '开发规范', or wants to produce a structured development specification for a new or existing project."
---

# Spec Orchestrator

Transform a project idea or existing codebase into a structured DEV_SPEC.md with 8 axioms, 6 sections, and phased task orchestration.

---

## Pipeline

```
Understand Project → Fill Sections → Generate Tasks → Output SPEC
```

## Workflow

### Step 1: Understand the Project

Gather context before writing. Ask the user or explore the codebase:

1. **What** does this project do? (one sentence)
2. **Why** does it exist? (problem + philosophy)
3. **Who** is it for? (target audience)
4. **What are the core features?** (3-7 features)
5. **What tech stack?** (language, frameworks, external services)
6. **What's the scope?** (in-scope vs explicitly out-of-scope)

If exploring an existing codebase, read key files: README, main entry point, config files, directory structure.

### Step 2: Generate the DEV_SPEC

Run the bootstrap script to create a skeleton from the template:

```bash
python .claude/skills/spec-orchestrator/scripts/init_spec.py <project_name> [--path <output_dir>]
```

This creates `DEV_SPEC.md` with all 6 sections pre-filled with placeholders.

### Step 3: Fill Each Section

Fill sections in this order (dependencies flow downward):

| Order | Section | Depends On | Key Questions |
|-------|---------|-----------|---------------|
| 1 | §1 Project Overview | Nothing | Why, who, scope |
| 2 | §5 Architecture | §1 | Layers, directory, data flow |
| 3 | §3 Tech Decisions | §5 | Interfaces, factories, config |
| 4 | §2 Core Features | §3 | Trade-offs, extension points |
| 5 | §4 Testing Strategy | §5 | Test pyramid, golden set |
| 6 | §6 Project Schedule | All above | Phases, ~1h tasks, acceptance criteria |

### Step 4: Validate the SPEC

Before finalizing, verify:

- [ ] Every task in §6 has: **objective, files, classes/functions, acceptance criteria, test method**
- [ ] Every pluggable component in §3 has: **interface, factory, config, implementation, fallback**
- [ ] §5 directory structure matches §6 task file lists
- [ ] No task exceeds ~1 hour of work (split if needed)
- [ ] Test methods reference actual test file paths

---

## 8 Axioms (embed in every SPEC)

1. **Spec before implementation** — interfaces + contracts + acceptance criteria defined first
2. **One hour, one verifiable increment** — every task ~1h with testable output
3. **Test-first, always** — define test method before writing code
4. **Interfaces before implementations** — abstract base + factory first, concrete backends second
5. **Configuration drives behavior** — single config file, zero code changes to switch
6. **Fail fast, degrade gracefully** — validate at startup, fallback at runtime
7. **Observability is not optional** — structured logging + trace context as first-class
8. **SPEC is a living document** — update progress table after every task

---

## Reference Map

| File | Content | When to Read |
|------|---------|-------------|
| `references/methodology_template.md` | Full template with all placeholders | When generating or editing a SPEC |
| `references/phase_guide.md` | Phase adaptation by project type | When deciding which phases to include |

---

## Task Card Format (every task in §6 must follow)

```markdown
### {ID}: {Name}
- **Objective**: one sentence
- **Files to Modify**:
  - `path/to/file`
- **Classes/Functions**:
  - `ClassName.method()` -> `ReturnType`
- **Acceptance Criteria**:
  - criterion 1
  - criterion 2
- **Test Method**: `pytest -q tests/unit/test_xxx.py`
```

---

## Pluggable Component Checklist (for every component in §3)

```
[ ] 1. Abstract interface (BaseX)
[ ] 2. Factory (XFactory.create reads config)
[ ] 3. Config entry (settings.yaml: x.backend)
[ ] 4. At least one concrete implementation
[ ] 5. Fallback/degradation strategy documented
```

---

## Phase Adaptation Guide

| Project Type | Keep | Drop | Add |
|-------------|------|------|-----|
| CLI Tool | A, B, C, D, I | E, F, G, H | CLI arg parsing |
| Web API | A, B, C, D, E, F, I | G(opt), H(opt) | Auth/Authz |
| Library/SDK | A, B, C, I | D, E, F, G, H | API docs, publish |
| Data Pipeline | A, B, C, F, H, I | E, G | Scheduling |
| Full App | All A-I | None | Frontend/UI |
| Microservice | A, B, C, D, E, F, I | G(opt) | Service mesh |
| AI/ML Project | A, B, C, D, F, H, I | E(opt), G(opt) | Model training |
