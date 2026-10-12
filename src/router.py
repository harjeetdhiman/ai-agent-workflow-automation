import logging
from typing import Optional, Dict
from src.schemas import WorkflowDefinition, WorkflowSelection
from src.loader import workflow_loader
from src.llm.base import BaseLLMProvider
from src.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


class WorkflowRouter:
    """
    Intelligent request router that maps natural-language user queries
    to the authoritative workflow registry parsed from Excel.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    def route(self, user_request: str) -> WorkflowSelection:
        """
        Analyzes the user's request and identifies the matching workflow.
        Performs strict validation against the registered workflows.
        """
        available_workflows = workflow_loader.get_all_workflows()

        if not user_request or not user_request.strip():
            return WorkflowSelection(
                workflow_id=None,
                workflow_name=None,
                confidence=0.0,
                reasoning="Empty request received.",
                is_ambiguous=False,
                clarification_prompt="Please provide a request or question describing the task you want to automate."
            )

        # Query LLM / Intent Engine
        selection = self.llm.route_request(user_request, available_workflows)

        # Validate identified workflow ID against registry
        if selection.workflow_id:
            if selection.workflow_id not in available_workflows:
                logger.warning(
                    f"Router suggested invalid workflow ID '{selection.workflow_id}' which is not in the registry. Rejecting."
                )
                selection.workflow_id = None
                selection.workflow_name = None
                selection.confidence = 0.0
                selection.reasoning = "Suggested workflow ID does not exist in registry."
            else:
                # Ensure exact official name from Excel is populated
                official_wf = available_workflows[selection.workflow_id]
                selection.workflow_name = official_wf.workflow_name

        return selection
