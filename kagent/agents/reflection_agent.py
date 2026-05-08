"""ReflectionAgent: Execute → Reflect → Refine iterative agent"""

from typing import Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.llm import AgentLLM
from ..core.message import Message


_INITIAL_PROMPT = """You are a helpful assistant. Answer the following question thoroughly.

Question: {input}
"""

_REFLECT_PROMPT = """You are reviewing an answer for quality. Analyze the answer and suggest improvements.

Original question: {question}

Current answer:
{answer}

If the answer is already excellent and needs no improvement, respond with EXACTLY:
无需改进

Otherwise, describe specific improvements that should be made. Be concise.
"""

_REFINE_PROMPT = """You are refining an answer based on feedback.

Original question: {question}

Previous answer:
{answer}

Feedback:
{feedback}

Provide an improved answer. Be thorough and address all feedback points.
"""


class ReflectionAgent(Agent):
    """Agent that iteratively improves its answer through self-reflection.

    Workflow: initial answer → reflect → refine → reflect → ... (up to max_steps)
    Stops early when reflection says "无需改进" (no improvement needed).
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

    def run(self, input_text: str, max_steps: Optional[int] = None, **kwargs) -> str:
        """Run the reflection loop on input_text.

        Args:
            input_text: User input / question.
            max_steps: Maximum reflection iterations. Defaults to config.max_steps.

        Returns:
            Best answer after reflection iterations.
        """
        max_steps = max_steps if max_steps is not None else self.config.max_steps
        self._new_run_id()
        self.add_message(Message(content=input_text, role="user"))

        # Phase 1: Generate initial answer
        answer = self._generate_initial(input_text)

        # Phase 2: Reflect and refine loop
        for _ in range(max_steps):
            feedback = self._reflect(input_text, answer)

            # Check if reflection says no improvement needed
            if "无需改进" in feedback:
                break

            answer = self._refine(input_text, answer, feedback)

        self.add_message(Message(content=answer, role="assistant"))
        return answer

    def _generate_initial(self, question: str) -> str:
        """Generate the initial answer."""
        prompt = (self.system_prompt or _INITIAL_PROMPT).format(input=question)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)
        return response.content or ""

    def _reflect(self, question: str, answer: str) -> str:
        """Reflect on the current answer and suggest improvements."""
        prompt = _REFLECT_PROMPT.format(question=question, answer=answer)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)
        return response.content or ""

    def _refine(self, question: str, answer: str, feedback: str) -> str:
        """Refine the answer based on reflection feedback."""
        prompt = _REFINE_PROMPT.format(
            question=question, answer=answer, feedback=feedback,
        )
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)
        return response.content or ""
