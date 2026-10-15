from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid
from datetime import datetime


class StepDefinition(BaseModel):
    """Declarative definition of a single executable step within a workflow pipeline."""
    model_config = ConfigDict(populate_by_name=True)

    step_number: int = Field(alias="step_order", default=1)
    step_name: str
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for the tool")
    input_source: Optional[str] = Field(None, description="Expression defining source of step input data")
    # Legacy single-field condition (kept for backward compat with synthesized steps)
    condition: Optional[str] = Field(None, description="Deprecated: use condition_expr instead")
    # Structured condition trio loaded from Excel columns Condition_Expr / On_True / On_False
    condition_expr: Optional[str] = Field(None, description="Safe Python expression evaluated against execution context")
    on_true: str = Field(default="continue", description="Branch action when condition_expr is True: continue|skip|stop|escalate|ask_user")
    on_false: str = Field(default="continue", description="Branch action when condition_expr is False: continue|skip|stop|escalate|ask_user")
    on_error: str = Field(default="stop", description="Action policy on failure: stop, continue, retry:N, escalate, fallback_llm")
    input_mappings: Dict[str, Any] = Field(default_factory=dict, description="Maps tool arguments to context expressions")
    output_variable: Optional[str] = Field(None, description="Key in execution context where tool output is stored")
    summary_template: Optional[str] = Field(None, description="Format string or summary pattern for this step")


class PreCondition(BaseModel):
    """Declarative pre-condition or validation gate required before step execution."""
    name: str
    required_keys: List[str] = Field(default_factory=list)
    rule_expression: str = ""
    failure_status: str = Field(default="NEEDS_INPUT", description="NEEDS_INPUT or FAILED")
    failure_message: str = ""


class WorkflowDefinition(BaseModel):
    """Represents a business workflow parsed dynamically from the Excel source with executable step specs."""
    workflow_id: str = Field(description="Unique workflow ID")
    workflow_name: str = Field(description="Descriptive name of the workflow")
    trigger: str = Field(default="", description="Trigger condition or user intent description")
    inputs: str = Field(default="", description="Raw description of required and optional inputs")
    steps_raw: str = Field(default="", description="Raw steps string from Excel separated by arrows")
    steps: List[str] = Field(default_factory=list, description="Ordered list of execution steps")
    decision_logic: str = Field(default="", description="Business logic, thresholds, or conditional rules")
    tools_required: List[str] = Field(default_factory=list, description="List of required tools")
    expected_output: str = Field(default="", description="Expected output format or deliverable")

    # Declarative execution specifications
    executable_steps: List[StepDefinition] = Field(default_factory=list, description="Data-driven executable steps")
    pre_conditions: List[PreCondition] = Field(default_factory=list, description="Input validation gates")
    spec_key: Optional[str] = Field(None, description="Key identifying the declarative execution specification")
    test_examples: List[str] = Field(default_factory=list, description="Test query examples from Excel")


class WorkflowSelection(BaseModel):
    """Result of intent analysis and workflow routing."""
    workflow_id: Optional[str] = Field(None, description="Identified Workflow ID or None if unsupported")
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
    status: str = Field(description="SUCCESS, FAILED, SKIPPED, or ESCALATED")
    tool_name: Optional[str] = None
    executed_by: str = Field(default="tool", description="'tool' = registered generic primitive; 'simulated' = offline LLM mock; 'llm' = real OpenAI call")
    tool_input: Optional[Dict[str, Any]] = None
    tool_output_summary: Optional[str] = None
    tool_output: Optional[Any] = None
    details: Optional[Any] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    retries: int = 0


class ConditionEvaluation(BaseModel):
    """Trace of a business condition or decision rule evaluated dynamically."""
    condition_name: str
    rule_expression: str
    outcome: bool
    explanation: str
    branch_taken: Optional[str] = Field(default="continue", description="Branch action taken based on outcome")


class WorkflowExecutionResult(BaseModel):
    """Complete, transparent execution trace and final output of the AI Agent System."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user_request: str
    selected_workflow_id: Optional[str] = None
    selected_workflow_name: Optional[str] = None
    selection_confidence: float = 0.0
    selection_reasoning: str = ""
    status: str = Field(description="SUCCESS, FAILED, NEEDS_INPUT, or ESCALATED")
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
