from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class WorkflowDefinition(BaseModel):
    """Represents a business workflow parsed dynamically from the Excel source."""
    workflow_id: str = Field(description="Unique workflow ID, e.g. WF001")
    workflow_name: str = Field(description="Descriptive name of the workflow")
    trigger: str = Field(description="Trigger condition or user intent description")
    inputs: str = Field(description="Raw description of required and optional inputs")
    steps_raw: str = Field(description="Raw steps string from Excel separated by arrows")
    steps: List[str] = Field(default_factory=list, description="Ordered list of execution steps")
    decision_logic: str = Field(description="Business logic, thresholds, or conditional rules")
    tools_required: List[str] = Field(default_factory=list, description="List of required tools")
    expected_output: str = Field(description="Expected output format or deliverable")


class WorkflowSelection(BaseModel):
    """Result of intent analysis and workflow routing."""
    workflow_id: Optional[str] = Field(None, description="Identified Workflow ID (e.g. WF001) or None if unsupported")
    workflow_name: Optional[str] = Field(None, description="Identified Workflow Name")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Routing confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Explanation of why this workflow was chosen")
    extracted_params: Dict[str, Any] = Field(default_factory=dict, description="Parameters extracted from user prompt")
    is_ambiguous: bool = Field(default=False, description="Flag indicating if multiple workflows matched")
    clarification_prompt: Optional[str] = Field(None, description="Question to ask if ambiguous or missing info")


class StepResult(BaseModel):
    """Trace of a single step execution within a workflow."""
    step_number: int
    step_name: str
    status: str = Field(description="SUCCESS, FAILED, or SKIPPED")
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output_summary: Optional[str] = None
    details: Optional[Any] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


class ConditionEvaluation(BaseModel):
    """Trace of a business condition or decision rule evaluated in Python."""
    condition_name: str
    rule_expression: str
    outcome: bool
    explanation: str


class WorkflowExecutionResult(BaseModel):
    """Complete, transparent execution trace and final output of the AI Agent System."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user_request: str
    selected_workflow_id: Optional[str] = None
    selected_workflow_name: Optional[str] = None
    selection_confidence: float = 0.0
    selection_reasoning: str = ""
    status: str = Field(description="SUCCESS, FAILED, or NEEDS_INPUT")
    steps_executed: List[StepResult] = Field(default_factory=list)
    conditions_evaluated: List[ConditionEvaluation] = Field(default_factory=list)
    tools_invoked: List[str] = Field(default_factory=list)
    final_result_data: Optional[Any] = None
    final_summary: str = ""
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class TestQuestion(BaseModel):
    """A test question loaded directly from the Excel Test_Questions sheet."""
    workflow_id: str
    test_request: str
    what_to_check: str
