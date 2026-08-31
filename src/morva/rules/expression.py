from __future__ import annotations

from decimal import Decimal
from typing import Mapping


class ExpressionError(ValueError):
    pass


def evaluate_expression(expression: Mapping[str, object], values: Mapping[str, Decimal]) -> Decimal:
    op = expression.get("op")
    if op == "const":
        return Decimal(str(expression.get("value", "0")))
    if op == "value":
        name = expression.get("name")
        if not isinstance(name, str):
            raise ExpressionError("value expression requires a string name")
        return Decimal(values.get(name, Decimal(0)))
    args = expression.get("args")
    if not isinstance(args, list):
        raise ExpressionError(f"{op} expression requires args")
    evaluated = [evaluate_expression(item, values) for item in args if isinstance(item, dict)]
    if len(evaluated) != len(args):
        raise ExpressionError("all expression args must be objects")
    if op == "add":
        return sum(evaluated, Decimal(0))
    if op == "sub":
        if len(evaluated) != 2:
            raise ExpressionError("sub requires two arguments")
        return evaluated[0] - evaluated[1]
    if op == "mul":
        result = Decimal(1)
        for item in evaluated:
            result *= item
        return result
    if op == "div":
        if len(evaluated) != 2 or evaluated[1] == 0:
            raise ExpressionError("div requires two arguments and non-zero denominator")
        return evaluated[0] / evaluated[1]
    if op == "min":
        return min(evaluated, default=Decimal(0))
    if op == "max":
        return max(evaluated, default=Decimal(0))
    raise ExpressionError(f"unsupported rule operation: {op}")
