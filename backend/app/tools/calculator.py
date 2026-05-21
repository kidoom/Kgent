"""A tiny safe calculator tool."""

import ast
import operator
from typing import Any


class CalculatorTool:
    name = "calculator"
    description = "Evaluate a simple arithmetic expression. Supports +, -, *, /, //, %, **, and parentheses."
    risk_level = "low"
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression to evaluate, for example: 12 * 8 + 6.",
            }
        },
        "required": ["expression"],
        "additionalProperties": False,
    }

    async def call(self, input: dict[str, Any]) -> str:
        expression = input.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("calculator requires a non-empty 'expression' string")
        result = _eval_expr(expression)
        return str(result)


_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_expr(expression: str) -> int | float:
    node = ast.parse(expression, mode="eval")
    return _eval_node(node.body)


def _eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BIN_OPS:
            raise ValueError(f"unsupported operator: {op_type.__name__}")
        return _ALLOWED_BIN_OPS[op_type](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY_OPS:
            raise ValueError(f"unsupported operator: {op_type.__name__}")
        return _ALLOWED_UNARY_OPS[op_type](_eval_node(node.operand))
    raise ValueError("expression contains unsupported syntax")
