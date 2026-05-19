## 9. Agent Loop 伪代码

```python
async def run_agent(user_input: str) -> AgentResult:
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=user_input),
    ]

    steps = []

    for step in range(MAX_STEPS):
        response = await call_model(
            messages=messages,
            tools=[tool_to_schema(tool) for tool in TOOLS],
        )

        messages.append(response.assistant_message)

        if not response.tool_uses:
            return AgentResult(answer=response.text, steps=steps)

        for tool_use in response.tool_uses:
            steps.append({
                "type": "tool_use",
                "name": tool_use.name,
                "input": tool_use.input,
            })

            result = await execute_tool_use(tool_use)

            steps.append({
                "type": "tool_result",
                "name": tool_use.name,
                "content": result.content,
                "is_error": result.is_error,
            })

            messages.append(Message(
                role="user",
                content=[ToolResultBlock(
                    tool_use_id=tool_use.id,
                    content=result.content,
                    is_error=result.is_error,
                )],
            ))

    raise RuntimeError("Agent stopped: max steps reached")
```
