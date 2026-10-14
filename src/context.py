from typing import Dict, Any, Optional


class ExecutionContext:
    """
    State manager for executing data-driven workflow steps.
    Passes inputs, parameters, and intermediate step outputs through the workflow DAG.
    """

    def __init__(self, user_request: str, params: Optional[Dict[str, Any]] = None):
        self.user_request = user_request
        self.params: Dict[str, Any] = dict(params or {})
        self.state: Dict[str, Any] = dict(self.params)
        self.step_outputs: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Stores a variable in the execution context state."""
        self.state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a variable from the context state or params."""
        return self.state.get(key, self.params.get(key, default))

    def resolve_value(self, val: Any) -> Any:
        """
        Resolves dynamic variable expressions:
        - '$params.key|default' -> retrieves from params with optional default
        - '$state.key|default'  -> retrieves from state with optional default
        - '$user_request'       -> retrieves raw user query
        """
        if not isinstance(val, str) or not val.startswith("$"):
            return val

        expr = val[1:]  # strip leading '$'
        default_val = None
        if "|" in expr:
            expr, raw_default = expr.split("|", 1)
            if raw_default.isdigit():
                default_val = int(raw_default)
            elif raw_default.replace(".", "", 1).isdigit() and raw_default.count(".") == 1:
                default_val = float(raw_default)
            elif raw_default.lower() == "true":
                default_val = True
            elif raw_default.lower() == "false":
                default_val = False
            else:
                default_val = raw_default

        if expr == "user_request":
            return self.user_request

        if expr.startswith("params."):
            key = expr.split(".", 1)[1]
            res = self.params.get(key)
            return res if res is not None else default_val

        if expr.startswith("state."):
            key = expr.split(".", 1)[1]
            res = self.state.get(key)
            return res if res is not None else default_val

        res = self.state.get(expr, self.params.get(expr))
        return res if res is not None else default_val

    def resolve_inputs(self, input_mappings: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves all input expressions against current context state."""
        resolved = {}
        for param_name, mapping in input_mappings.items():
            resolved[param_name] = self.resolve_value(mapping)
        return resolved
