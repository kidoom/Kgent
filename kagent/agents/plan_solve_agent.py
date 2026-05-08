"""PlanAndSolveAgent: Plan → Execute two-phase reasoning"""

import ast
from typing import Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.exceptions import AgentError
from ..core.llm import AgentLLM
from ..core.message import Message


_DEFAULT_PLAN_PROMPT = """You are a helpful assistant that solves problems by first creating a plan, then executing each step.

Given the user's question, first create a step-by-step plan as a Python list of strings.
Then execute each step sequentially.

To create a plan, respond with ONLY a Python list of strings, like:
["Step 1: ...", "Step 2: ...", "Step 3: ..."]

Do NOT include any other text, just the Python list.

Question: {input}
"""

_DEFAULT_EXECUTE_PROMPT = """You are executing a plan to answer a question.

Original question: {question}

Plan:
{plan}

Progress so far:
{progress}

Current step: {current_step}

Execute this step and provide the result. Be concise.
"""


class PlanAndSolveAgent(Agent):
    """Agent that solves problems in two phases: Plan then Execute.

    Phase 1 (_plan): Ask LLM to generate a Python list of steps.
    Phase 2 (_execute): Execute each step sequentially with full context.
    """

    def __init__(
        self,
        name: str,
        llm: AgentLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompt: Optional[str] = None,
    ):
        super().__init__(
            name=name, llm=llm, system_prompt=system_prompt,
            config=config, custom_prompt=custom_prompt,
        )

    def run(self, input_text: str, **kwargs) -> str:
        """Run plan-then-execute on input_text.

        Args:
            input_text: User input / question.

        Returns:
            Final answer string.

        Raises:
            AgentError: If plan parsing fails.
        """
        self._new_run_id()
        self.add_message(Message(content=input_text, role="user"))

        # Phase 1: Plan
        plan = self._plan(input_text)

        # Phase 2: Execute
        result = self._execute(input_text, plan)

        self.add_message(Message(content=result, role="assistant"))
        return result

    def _plan(self, question: str) -> list[str]:
        """Ask LLM to generate a step-by-step plan.

        Returns:
            List of step strings.

        Raises:
            AgentError: If LLM output cannot be parsed as a list.
        """
        prompt = self.system_prompt or _DEFAULT_PLAN_PROMPT
        messages = [{"role": "user", "content": prompt.format(input=question)}]

        response = self.llm.invoke(messages)
        content = response.content or ""

        # Parse the plan as a Python list
        try:
            plan = ast.literal_eval(content.strip())
        except (ValueError, SyntaxError) as e:
            raise AgentError(
                user_message="无法解析执行计划，请重试",
                debug_message=f"Plan parse failed: {e}, LLM output: {content!r}",
            ) from e

        if not isinstance(plan, list) or not all(isinstance(s, str) for s in plan):
            raise AgentError(
                user_message="执行计划格式错误，需要字符串列表",
                debug_message=f"Expected list[str], got {type(plan).__name__}: {plan!r}",
            )

        return plan

    def _execute(self, question: str, plan: list[str]) -> str:
        """Execute each plan step sequentially with full context.

        Returns:
            Final result from the last step.
        """
        progress_lines: list[str] = []
        result = ""

        for i, step in enumerate(plan):
            progress_str = "\n".join(progress_lines) if progress_lines else "(none yet)"

            prompt = _DEFAULT_EXECUTE_PROMPT.format(
                question=question,
                plan="\n".join(f"  {j+1}. {s}" for j, s in enumerate(plan)),
                progress=progress_str,
                current_step=step,
            )
            messages = [{"role": "user", "content": prompt}]

            response = self.llm.invoke(messages)
            result = response.content or ""

            progress_lines.append(f"Step {i+1}: {step}\nResult: {result}")

        return result
