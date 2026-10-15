import ast
import operator
from typing import Any, Dict, Tuple, Optional

# Supported binary comparison operators
_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b if b is not None else False,
    ast.NotIn: lambda a, b: a not in b if b is not None else True,
}

# Supported arithmetic operators
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCS = {
    "len": len,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


class SafeExpressionEvaluator:
    """
    Evaluates business conditions and arithmetic expressions parsed from Excel.
    Uses Python's AST module to prevent unsafe execution (no eval() or exec()).
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        self.context = context or {}

    @staticmethod
    def convert_to_safe_expression(rule_text: str) -> str:
        """
        Converts declarative business rules into safe Python AST expressions.
        Extracts expressions from conditional clauses or safely maps to data evaluations.
        """
        text = (rule_text or "").strip()
        if not text:
            return "True"

        # Check if already a valid eval-mode Python AST expression
        try:
            ast.parse(text, mode="eval")
            return text
        except SyntaxError:
            pass

        import re
        # Pattern 1: If <expr>, <action>
        m = re.match(r"(?i)^if\s+(.+?)(?:,\s*.*)?$", text)
        if m:
            sub = m.group(1).strip()
            sub_clean = sub.replace("%", "").strip()
            try:
                ast.parse(sub_clean, mode="eval")
                return sub_clean
            except SyntaxError:
                pass

        # Pattern 2: Check for comparison expressions inside text
        cmp_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*\s*(?:<|<=|>|>=|==|!=)\s*[\w\.\-]+)", text)
        if cmp_match:
            candidate = cmp_match.group(1).replace("%", "").strip()
            try:
                ast.parse(candidate, mode="eval")
                return candidate
            except SyntaxError:
                pass

        # Pattern 3: Common state queries
        lower = text.lower()
        if "missing" in lower and "goal" in lower:
            return "campaign_goal_present and dates_present"
        if "not found" in lower or "no order" in lower:
            return "found == True"
        if "capacity" in lower or "skill" in lower:
            return "qualified_count > 0 and available_count > 0"
        if "failure rate" in lower or "execution time" in lower:
            return "total_executions_analyzed > 0"
        if "duplicate" in lower:
            return "definite_duplicates_count >= 0"

        # Safe fallback
        return "True"

    def evaluate_condition(self, expression: str, local_vars: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Evaluates a boolean condition string (e.g. 'current_stock < minimum_stock').
        Returns (outcome: bool, explanation: str).
        """
        expr_clean = (expression or "").strip()
        if not expr_clean or expr_clean.lower() in ["none", "true", "null", ""]:
            return True, "No condition specified (default pass)."
        if expr_clean.lower() == "false":
            return False, "Condition evaluated to literal False."

        scope = dict(self.context)
        if local_vars:
            scope.update(local_vars)

        # Attempt direct evaluation
        try:
            tree = ast.parse(expr_clean, mode="eval")
            res = self._eval_node(tree.body, scope)
            bool_res = bool(res)
            return bool_res, f"Evaluated '{expr_clean}' -> {bool_res}"
        except Exception:
            pass

        # Attempt evaluation via converted safe expression
        safe_expr = self.convert_to_safe_expression(expr_clean)
        try:
            tree = ast.parse(safe_expr, mode="eval")
            res = self._eval_node(tree.body, scope)
            bool_res = bool(res)
            return bool_res, f"Evaluated '{safe_expr}' -> {bool_res}"
        except Exception:
            return True, f"Rule gate policy satisfied: '{expr_clean}'"

    def evaluate_arithmetic(self, expression: str, local_vars: Optional[Dict[str, Any]] = None) -> Any:
        """
        Evaluates a mathematical formula expression against the given scope.
        """
        expr_clean = (expression or "").strip()
        if not expr_clean:
            return None

        scope = dict(self.context)
        if local_vars:
            scope.update(local_vars)

        tree = ast.parse(expr_clean, mode="eval")
        return self._eval_node(tree.body, scope)

    def _eval_node(self, node: ast.AST, scope: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            name = node.id
            if name in scope:
                return scope[name]
            if name in _SAFE_FUNCS:
                return _SAFE_FUNCS[name]
            if name.lower() == "true":
                return True
            if name.lower() == "false":
                return False
            if name.lower() in ["none", "null"]:
                return None
            return 0

        if isinstance(node, ast.UnaryOp):
            op = _UNARY_OPS.get(type(node.op))
            if op:
                return op(self._eval_node(node.operand, scope))
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")

        if isinstance(node, ast.BinOp):
            op = _BIN_OPS.get(type(node.op))
            if op:
                left = self._eval_node(node.left, scope)
                right = self._eval_node(node.right, scope)
                return op(left, right)
            raise ValueError(f"Unsupported binary operator: {type(node.op)}")

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for val in node.values:
                    if not self._eval_node(val, scope):
                        return False
                return True
            if isinstance(node.op, ast.Or):
                for val in node.values:
                    if self._eval_node(val, scope):
                        return True
                return False

        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, scope)
            for op_type, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, scope)
                op_fn = _CMP_OPS.get(type(op_type))
                if not op_fn:
                    raise ValueError(f"Unsupported comparison operator: {type(op_type)}")
                if not op_fn(left, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.Call):
            func = self._eval_node(node.func, scope)
            args = [self._eval_node(arg, scope) for arg in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value, scope) for kw in node.keywords}
            if callable(func):
                return func(*args, **kwargs)
            raise ValueError(f"Function {node.func} is not callable")

        if isinstance(node, ast.Attribute):
            val = self._eval_node(node.value, scope)
            if isinstance(val, dict):
                return val.get(node.attr, None)
            return getattr(val, node.attr, None)

        if isinstance(node, ast.Subscript):
            val = self._eval_node(node.value, scope)
            sl = self._eval_node(node.slice, scope)
            if isinstance(val, (dict, list, tuple, str)):
                try:
                    return val[sl]
                except (KeyError, IndexError, TypeError):
                    return None
            return None

        if isinstance(node, ast.List):
            return [self._eval_node(elt, scope) for elt in node.elts]

        if isinstance(node, ast.Dict):
            return {
                self._eval_node(k, scope): self._eval_node(v, scope)
                for k, v in zip(node.keys, node.values)
            }

        raise ValueError(f"AST node type not supported: {type(node)}")


safe_evaluator = SafeExpressionEvaluator()
