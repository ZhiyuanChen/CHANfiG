# CHANfiG
# Copyright (C) 2022-Present, DanLing Team
#
# This file is part of CHANfiG.
#
# CHANfiG is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - The Unlicense
# - GNU Affero General Public License v3.0 or later
# - GNU General Public License v2.0 or later
# - BSD 4-Clause "Original" or "Old" License
# - MIT License
# - Apache License 2.0
#
# CHANfiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

from __future__ import annotations

import ast
import operator
from typing import Any, Mapping


class SafeEvalError(Exception):
    """Raised when an expression cannot be safely evaluated."""


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


def safe_eval_expr(expression: str, context: Mapping[str, Any]) -> Any:
    """
    Safely evaluate a limited arithmetic expression against a context of names.

    Supported:
        - Literals (ints, floats, strings)
        - Names (looked up in `context`)
        - Unary +/- on numbers
        - Binary ops: +, -, *, /, //, %, **
        - Parentheses (handled by the AST parser)

    Anything else raises SafeEvalError.
    """

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:  # pragma: no cover - defensive
        raise SafeEvalError(f"Invalid expression: {expression!r}") from exc

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in context:
                raise SafeEvalError(f"Unknown name: {node.id}")
            return context[node.id]
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
            operand = _eval(node.operand)
            return _ALLOWED_UNARY_OPS[type(node.op)](operand)
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
            left = _eval(node.left)
            right = _eval(node.right)
            return _ALLOWED_BIN_OPS[type(node.op)](left, right)
        raise SafeEvalError(f"Unsupported expression: {expression!r}")

    return _eval(tree)
