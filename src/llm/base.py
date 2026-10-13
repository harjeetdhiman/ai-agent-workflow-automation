from abc import ABC, abstractmethod
from typing import Dict
from src.schemas import WorkflowDefinition, WorkflowSelection


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def route_request(
        self,
        user_request: str,
        available_workflows: Dict[str, WorkflowDefinition]
    ) -> WorkflowSelection:
        """Analyzes user request and returns identified workflow, confidence, and extracted parameters."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        """Generates text from a prompt."""
        pass
