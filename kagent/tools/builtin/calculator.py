"""CalculatorTool: safe expression evaluation using AST"""

import ast
import math
import operator

from ..base import Tool, ToolResult, ToolParameter


class CalculatorTool(Tool):
    """Safely evaluate mathematical expressions using AST parsing"""

    # Allowed operators
    _operators: dict[type, callable] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Allowed math functions
    _functions: dict[str, callable] = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
        "pi": lambda: math.pi,
        "e": lambda: math.e,
    }

    def __init__(self):
        super().__init__(
            name="calculator",
            description="安全计算数学表达式，支持 +-*/、括号、sqrt/sin/cos/log/exp 等函数",
        )

    def run(self, parameters: dict) -> ToolResult:
        expression = parameters.get("expression", "").strip()
        if not expression:
            return ToolResult(
                content="表达式不能为空",
                success=False,
                error="empty_expression",
            )

        try:
            result = self._eval_expr(expression)
            return ToolResult(
                content=str(result),
                success=True,
                metadata={"expression": expression},
            )
        except ZeroDivisionError:
            return ToolResult(
                content="[ERROR] 除数不能为零",
                success=False,
                error="division_by_zero",
            )
        except Exception as e:
            return ToolResult(
                content=f"[ERROR] 表达式无效: {e}",
                success=False,
                error=str(e),
            )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="数学表达式，例如: 2+3*4, sqrt(16), sin(pi/2)",
                required=True,
            ),
        ]

    def _eval_expr(self, expr: str) -> float:
        """Safely evaluate an expression using AST."""
        tree = ast.parse(expr, mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node) -> float:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self._operators[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise ValueError(f"不支持的操作符: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return self._operators[op_type](operand)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name not in self._functions:
                    raise ValueError(f"不支持的函数: {name}")
                args = [self._eval_node(a) for a in node.args]
                return self._functions[name](*args)

        # Handle named constants: pi -> math.pi, e -> math.e
        if isinstance(node, ast.Name):
            name = node.id
            if name not in self._functions:
                raise ValueError(f"不支持的变量: {name}")
            return self._functions[name]()

        raise ValueError(f"不支持的语法: {type(node).__name__}")
