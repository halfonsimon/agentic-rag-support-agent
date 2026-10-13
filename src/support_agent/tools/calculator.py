"""Bounded numeric AST evaluation without eval or exec."""

from __future__ import annotations

import ast
import json
import math
import operator
from typing import Any

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_ALLOWED_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_ALLOWED_FUNCS = {"round": round, "abs": abs, "min": min, "max": max}


def _bounded(value: int | float) -> int | float:
    if isinstance(value, complex) or not math.isfinite(value) or abs(value) > 1e100:
        raise ValueError("result must be finite and have magnitude at most 1e100")
    return value


def _eval_node(node: Any) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise ValueError("only numeric constants are allowed")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent magnitude must be at most 100")
        return _bounded(_ALLOWED_BINOPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise ValueError("only round/abs/min/max function calls are allowed")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed")
        return _ALLOWED_FUNCS[node.func.id](*[_eval_node(a) for a in node.args])
    raise ValueError(f"unsupported expression element: {type(node).__name__}")


def calculator(expression: str) -> str:
    """Safely evaluate a single arithmetic expression."""
    try:
        if len(str(expression)) > 1000:
            raise ValueError("expression is too long")
        tree = ast.parse(str(expression), mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 100:
            raise ValueError("expression has too many nodes")
        result = _bounded(_eval_node(tree))
        if isinstance(result, float):
            result = round(result, 10)
        return json.dumps({"expression": str(expression), "result": result})
    except Exception as exc:
        return json.dumps({"error": f"could not evaluate '{expression}': {exc}"})
