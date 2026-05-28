"""Interactive debug CLI for observing the agent runtime.

Default: sustained REPL (multi-turn, same session + reused API client).
One-shot: pass --once "your message" or positional message.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from typing import Any

from app.runtime.loop import run_agent_stream
from app.runtime.messages import AgentStep, Message, ToolResultBlock, ToolUseBlock
from app.model_client import ModelClientError, ModelClientProtocol, available_providers, build_model_client
from app.runtime.host import CLIHost
from app.runtime.permissions import (
    AllowAllPolicy,
    AskPolicy,
    PermissionPolicy,
    RiskBasedPolicy,
    normalize_mode,
)
from app.runtime.subagent import reset_active_host, set_active_host
from app.tools.registry import build_subagent_runner
from app.runtime.protocol import PermissionRequest, ResolvedPermission
from app.memory.session_store import get_or_create_session, reset_sessions
from app.core.config import (
    dotenv_path,
    find_repo_root,
    get_dotenv_settings,
    mask_secret,
    reload_dotenv_settings,
)
from app.tools.registry import build_tools

DEFAULT_DEBUG_SESSION = "debug-cli"

_TRACE_TITLES = {
    "after_user_append": "CHECKPOINT 0 | after user append",
    "turn_begin": "CHECKPOINT | turn {turn} begin (enter for-loop)",
    "after_plan": "CHECKPOINT | turn {turn} after plan phase (think, text-only, debug CLI)",
    "after_act": "CHECKPOINT | turn {turn} after act phase (tools or final, debug CLI)",
    "after_model": "CHECKPOINT | turn {turn} after call_model (+assistant / think)",
    "after_think_placeholder": "CHECKPOINT | turn {turn} placeholder think (no visible text)",
    "after_permission": "CHECKPOINT | turn {turn} after permission decision (deny/ask)",
    "after_tool": "CHECKPOINT | turn {turn} after tool (+tool_result)",
    "complete": "CHECKPOINT | turn {turn} complete (no tools, returning)",
}

_HELP_TEXT = """
Commands:
  /help, /?          show this help
  /reset             clear session messages (same session_id)
  /history           print current session messages index
  exit, quit         leave interactive mode
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kgent debug CLI — default is interactive multi-turn REPL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.cli.debug
  python -m app.cli.debug --once "帮我算一下 12 * 8 + 6"
  python -m app.cli.debug --once "帮我算一下 12 * 8 + 6"
  python -m app.cli.debug --compact --once "帮我算一下 12 * 8 + 6"
        """.strip(),
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact trace: checkpoint title + message count only; print steps (no full messages table).",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="If provided, runs one shot and exits (same as --once). Omit for interactive REPL.",
    )
    parser.add_argument("--once", metavar="TEXT", help="Run a single message and exit.")
    parser.add_argument("--show-system", action="store_true", help="Show full system message in messages dumps.")
    parser.add_argument("--max-steps", type=int, default=None, help="Override configured max steps.")
    parser.add_argument(
        "--session-id",
        default=DEFAULT_DEBUG_SESSION,
        help="Session id for short-term memory (interactive mode reuses the same session).",
    )
    parser.add_argument("--fresh-session", action="store_true", help="Clear session history before starting.")
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Only print final answer (skip per-turn messages/steps trace).",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Override KGENT_PROVIDER (default: read from .env, typically openai/DeepSeek).",
    )
    parser.add_argument(
        "--permission",
        choices=["allow_all", "risk_based", "interactive"],
        default=None,
        help="Override KGENT_PERMISSION_MODE for this run (default: read from .env, falls back to interactive in CLI).",
    )
    args = parser.parse_args()

    if args.fresh_session:
        reset_sessions()

    once_text = (args.once or "").strip() or " ".join(args.message).strip()
    if once_text:
        asyncio.run(_run_single_shot(args, once_text))
        return

    asyncio.run(_run_interactive(args))


async def _run_interactive(args: argparse.Namespace) -> None:
    context = await _build_runtime(args)
    if context is None:
        return

    model_client, tools, step_limit, settings, provider, tracer, policy, permission_mode = context
    _print_startup_config(settings, provider, step_limit, args.session_id, permission_mode)

    print("\n=== Kgent Interactive Debug CLI ===")
    print(f"session_id: {args.session_id} (messages persist across turns)")
    print(f"provider: {provider} | model: {settings.model}")
    print(f"permission_mode: {permission_mode}")
    print("Debug mode: each loop turn runs plan (text-only) then act (tools/final).")
    if args.compact:
        print("Trace: --compact (steps only, no messages table). Use /history to dump messages.")
    print("Multi-turn REPL — type a message and press Enter. Same API client for the whole session.")
    print(_HELP_TEXT.strip())

    try:
        while True:
            try:
                user_input = (await asyncio.to_thread(input, "\nuser> ")).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye.")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                print("bye.")
                break
            if user_input.lower() in {"/help", "/?"}:
                print(_HELP_TEXT.strip())
                continue
            if user_input.lower() == "/reset":
                reset_sessions()
                print(f"session '{args.session_id}' cleared.")
                continue
            if user_input.lower() == "/history":
                _print_session_history(args.session_id, show_system=args.show_system)
                continue

            await _run_turn(
                user_input=user_input,
                model_client=model_client,
                tools=tools,
                step_limit=step_limit,
                session_id=args.session_id,
                max_session_messages=settings.max_session_messages,
                trace=not args.no_trace,
                tracer=tracer,
                policy=policy,
            )
    finally:
        if hasattr(model_client, "close"):
            await model_client.close()


async def _run_single_shot(args: argparse.Namespace, user_input: str) -> None:
    context = await _build_runtime(args)
    if context is None:
        return

    model_client, tools, step_limit, settings, provider, tracer, policy, permission_mode = context
    _print_startup_config(settings, provider, step_limit, args.session_id, permission_mode)
    try:
        await _run_turn(
            user_input=user_input,
            model_client=model_client,
            tools=tools,
            step_limit=step_limit,
            session_id=args.session_id,
            max_session_messages=settings.max_session_messages,
            trace=not args.no_trace,
            tracer=tracer,
            policy=policy,
        )
    finally:
        if hasattr(model_client, "close"):
            await model_client.close()

        print("\nTip: run `python -m app.cli.debug` with no arguments for sustained interactive mode.")


async def _build_runtime(
    args: argparse.Namespace,
) -> tuple[ModelClientProtocol, list, int, Any, str, Any, PermissionPolicy, str] | None:
    reload_dotenv_settings()
    settings = get_dotenv_settings()
    provider = args.provider or settings.provider
    step_limit = args.max_steps if args.max_steps is not None else settings.max_steps

    if provider == "openai" and not settings.api_key:
        env_file = dotenv_path()
        print(
            "\n[config-error] KGENT_PROVIDER=openai but KGENT_API_KEY is empty. "
            f"Set it in {env_file} (DeepSeek: KGENT_BASE_URL=https://api.deepseek.com)."
        )
        return None

    if provider not in available_providers():
        print(
            f"\n[config-error] Unknown provider '{provider}'. "
            f"Available: {', '.join(available_providers()) or '(none)'}"
        )
        return None

    try:
        model_client = build_model_client(provider, **settings.model_kwargs)
    except ModelClientError as exc:
        print(f"\n[model-client-error] {exc}")
        return None

    tools = build_tools(settings.project_root)
    tracer = (
        _make_tracer(show_system=args.show_system, compact=args.compact)
        if not args.no_trace
        else None
    )
    permission_mode = normalize_mode(args.permission or settings.permission_mode or "interactive")
    policy = _build_cli_policy(permission_mode)

    session_id = args.session_id
    subagent_runner = build_subagent_runner(
        model_client=model_client,
        parent_session_id=session_id,
        project_root=settings.project_root,
        policy=policy,
    )
    tools = build_tools(
        settings.project_root,
        session_id=session_id,
        subagent_runner=subagent_runner,
        include_task_tool=True,
    )
    return model_client, tools, step_limit, settings, provider, tracer, policy, permission_mode


def _build_cli_policy(mode: str) -> PermissionPolicy:
    if mode == "allow_all":
        return AllowAllPolicy()
    if mode == "risk_based":
        return RiskBasedPolicy()
    return AskPolicy()


async def _stdin_permission_resolver(request: PermissionRequest) -> ResolvedPermission:
    prompt = (
        f"\n[permission] tool={request.tool_name} risk={request.risk_level} "
        f"input={json.dumps(request.tool_input, ensure_ascii=False)} approve? [y/N] "
    )
    answer = (await asyncio.to_thread(input, prompt)).strip().lower()
    if answer in {"y", "yes"}:
        return ResolvedPermission(action="allow", reason="user approved")
    return ResolvedPermission(action="deny", reason="user rejected")


def _print_startup_config(
    settings: Any,
    provider: str,
    step_limit: int,
    session_id: str,
    permission_mode: str,
) -> None:
    print("\n=== Configuration ===")
    print("config mode: .env first (debug CLI)")
    print(f"repo_root: {find_repo_root()}")
    env_file = dotenv_path()
    print(f"dotenv: {env_file} ({'found' if env_file.exists() else 'missing'})")
    print(f"provider: {provider}")
    print(f"model: {settings.model}")
    print(f"base_url: {settings.base_url}")
    print(f"api_key: {mask_secret(settings.api_key)}")
    print(f"available_providers: {', '.join(available_providers())}")
    print(f"project_root: {settings.project_root}")
    print(f"max_steps: {step_limit}")
    print(f"session_id: {session_id}")
    print(f"max_session_messages: {settings.max_session_messages}")
    print(f"permission_mode: {permission_mode}")


async def _run_turn(
    user_input: str,
    model_client: ModelClientProtocol,
    tools: list,
    step_limit: int,
    session_id: str,
    max_session_messages: int,
    trace: bool,
    tracer: Any,
    policy: PermissionPolicy,
) -> None:
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    asker = _stdin_permission_resolver if isinstance(policy, AskPolicy) else None
    host = CLIHost(
        run_id=run_id,
        session_id=session_id,
        asker=asker,
        on_step=(lambda step: print_agent_step(step, indent="  ")) if trace else None,
    )
    token = set_active_host(host)
    try:
        result = await run_agent_stream(
            run_id=run_id,
            session_id=session_id,
            message=user_input,
            model_client=model_client,
            tools=tools,
            host=host,
            policy=policy,
            max_steps=step_limit,
            max_session_messages=max_session_messages,
            on_trace=tracer if trace else None,
            plan_before_act=True,
        )
    except ModelClientError as exc:
        print(f"\n[model-error] {exc}")
        return
    finally:
        reset_active_host(token)

    if not trace:
        print("\n=== Agent Loop (summary) ===")
        for step in result.steps:
            print_agent_step(step)

    print("\n" + "=" * 60)
    print("=== FINAL ANSWER ===")
    print(result.answer)
    print(f"\nsession_id: {result.session_id}")
    print(f"message_count in session: {result.message_count}")
    print(f"steps this turn: {len(result.steps)}")


def _print_session_history(session_id: str, show_system: bool) -> None:
    messages = get_or_create_session(session_id)
    print(f"\n=== Session history ({session_id}) | {len(messages)} messages ===")
    print_messages_table(messages, show_system=show_system)


def _make_tracer(show_system: bool, *, compact: bool = False):
    def on_trace(
        event: str,
        turn_index: int,
        messages: list[Message],
        added_steps: list[AgentStep],
    ) -> None:
        title = _TRACE_TITLES.get(event, event)
        if "{turn}" in title:
            title = title.format(turn=turn_index)
        print("\n" + "=" * 60)
        print(f"=== {title} ===")
        print(f"messages (len={len(messages)})")
        if compact:
            if added_steps:
                for step in added_steps:
                    print_agent_step(step, indent="  ")
            return
        print_messages_table(messages, show_system=show_system)
        if added_steps:
            print("\nsteps added:")
            for step in added_steps:
                print_agent_step(step, indent="  ")

    return on_trace


def print_messages_table(messages: list[Message], show_system: bool) -> None:
    for index, message in enumerate(messages):
        print(f"  [{index}] role={message.role:<9} {_format_message_content(message, show_system)}")


def _format_message_content(message: Message, show_system: bool) -> str:
    if message.role == "system" and not show_system:
        text = message.content if isinstance(message.content, str) else ""
        preview = text[:60].replace("\n", " ")
        return f'<system hidden, {len(text)} chars> "{preview}..."'

    if isinstance(message.content, str):
        return _preview_text(message.content)

    parts: list[str] = []
    if message.role == "assistant" and message.assistant_text:
        parts.append(f"plan: {_preview_text(message.assistant_text, 100)}")
    for block in message.content:
        if isinstance(block, ToolUseBlock):
            parts.append(f"tool_use {block.name}({block.id}) {_json_one_line(block.input)}")
        elif isinstance(block, ToolResultBlock):
            flag = " ERROR" if block.is_error else ""
            parts.append(f"tool_result{flag} for {block.tool_use_id}: {_preview_text(block.content, 80)}")
    return " | ".join(parts)


def _preview_text(text: str, limit: int = 120) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return repr(one_line)
    return repr(one_line[: limit - 3] + "...")


def _json_one_line(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def print_agent_step(step: AgentStep, indent: str = "") -> None:
    prefix = indent
    if step.type == "think":
        print(f"{prefix}[think] turn={step.turn_index}")
        print(f"{prefix}  {step.content or ''}")
    elif step.type == "call":
        decision = step.decision or "allow"
        print(
            f"{prefix}[call] turn={step.turn_index} tool={step.tool_name} "
            f"id={step.tool_use_id} decision={decision}"
        )
        print(f"{prefix}  input: {_json(step.tool_input or {})}")
    elif step.type == "observe":
        print(f"{prefix}[observe] turn={step.turn_index} tool={step.tool_name} error={step.is_error}")
        print(f"{prefix}  {step.content or ''}")
    elif step.type == "final":
        print(f"{prefix}[final] turn={step.turn_index}")
        print(f"{prefix}  {step.content or ''}")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
