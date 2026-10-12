import inspect
import logging
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all tools, APIs, and business functions.
    Supports declarative registration, argument validation, and exception isolation.
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}

    def register(self, name: str, description: str = "") -> Callable:
        """Decorator to register a function as a reusable tool."""
        def decorator(func: Callable) -> Callable:
            tool_name = name.lower().strip()
            self._tools[tool_name] = func
            self._descriptions[tool_name] = description or (func.__doc__ or "").strip()
            logger.debug(f"Registered tool: '{tool_name}'")
            return func
        return decorator

    def execute(self, tool_name: str, **kwargs) -> Any:
        """Executes a registered tool with error trapping and parameter filtering."""
        norm_name = tool_name.lower().strip()
        if norm_name not in self._tools:
            raise KeyError(
                f"Tool '{norm_name}' is not registered in the tool registry. "
                f"Available tools: {list(self._tools.keys())}"
            )

        func = self._tools[norm_name]
        sig = inspect.signature(func)

        # Filter arguments to match the function's signature
        has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if has_kwargs:
            filtered_args = kwargs
        else:
            filtered_args = {k: v for k, v in kwargs.items() if k in sig.parameters}

        try:
            return func(**filtered_args)
        except Exception as e:
            logger.error(f"Error executing tool '{norm_name}': {e}", exc_info=True)
            raise e

    def get_description(self, tool_name: str) -> str:
        return self._descriptions.get(tool_name.lower().strip(), "")

    def list_tools(self) -> Dict[str, str]:
        return dict(self._descriptions)


# Global singleton tool registry
tool_registry = ToolRegistry()
