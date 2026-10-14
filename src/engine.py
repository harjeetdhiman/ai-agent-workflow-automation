import time
import uuid
import logging
from typing import Dict, Any, Optional, List

from src.schemas import (
    WorkflowSelection,
    StepResult,
    ConditionEvaluation,
    WorkflowExecutionResult,
    WorkflowDefinition,
)
from src.loader import workflow_loader
from src.router import WorkflowRouter
from src.tools.registry import tool_registry
from src.llm.base import BaseLLMProvider
from src.llm.factory import get_llm_provider
from src.context import ExecutionContext
from src.workflow_specs import get_workflow_spec, WorkflowSpec

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Universal Data-Driven Workflow Execution Engine.
    Interprets declarative workflow definitions derived dynamically from the Excel specification.
    Contains ZERO hardcoded workflow ID branches (no 'if wf_id == WF001').
    All workflows (WF001 through WF010 and dynamic extensions like WF011) are executed
    through the common step-orchestration and tool-dispatch pipeline.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()
        self.router = WorkflowRouter(self.llm)

    def execute_request(self, user_request: str, override_params: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        """
        Executes a user request end-to-end through the common generic workflow pipeline:
        1. Natural language routing and parameter extraction.
        2. Declarative pre-condition validation.
        3. Context-driven ordered step execution via central ToolRegistry.
        4. Deterministic decision rule evaluation.
        5. Structured trace compilation and output synthesis.
        """
        start_time = time.time()
        exec_id = str(uuid.uuid4())[:8]

        # 1. Routing & Intent Recognition
        selection: WorkflowSelection = self.router.route(user_request)

        # Handle unrecognized or ambiguous requests
        if not selection.workflow_id:
            status = "NEEDS_INPUT" if selection.is_ambiguous else "FAILED"
            duration = round(time.time() - start_time, 3)
            return WorkflowExecutionResult(
                execution_id=exec_id,
                user_request=user_request,
                selected_workflow_id=None,
                selected_workflow_name=None,
                selection_confidence=selection.confidence,
                selection_reasoning=selection.reasoning,
                status=status,
                steps_executed=[],
                conditions_evaluated=[],
                tools_invoked=[],
                final_result_data=None,
                final_summary=selection.clarification_prompt or selection.reasoning,
                duration_seconds=duration,
                error_message=None if status == "NEEDS_INPUT" else "No matching workflow could be identified."
            )

        wf_def = workflow_loader.get_workflow(selection.workflow_id)
        if not wf_def:
            duration = round(time.time() - start_time, 3)
            return WorkflowExecutionResult(
                execution_id=exec_id,
                user_request=user_request,
                selected_workflow_id=selection.workflow_id,
                selected_workflow_name=selection.workflow_name,
                selection_confidence=selection.confidence,
                selection_reasoning=selection.reasoning,
                status="FAILED",
                steps_executed=[],
                conditions_evaluated=[],
                tools_invoked=[],
                final_result_data=None,
                final_summary="Identified workflow definition was not found in the loaded Excel registry.",
                duration_seconds=duration,
                error_message=f"Workflow definition missing for ID {selection.workflow_id}"
            )

        # Merge extracted params with runtime overrides
        params = dict(selection.extracted_params)
        if override_params:
            params.update(override_params)

        # 2. Retrieve Declarative Execution Specification
        spec: WorkflowSpec = get_workflow_spec(wf_def)

        # 3. Initialize Execution Context
        context = ExecutionContext(user_request=user_request, params=params)

        steps_executed: List[StepResult] = []
        conditions_evaluated: List[ConditionEvaluation] = []
        tools_invoked: List[str] = []
        status = "SUCCESS"
        err_msg = None
        final_data = None
        final_summary = ""

        try:
            # 4. Pre-execution Input Validation Gates
            pre_failure = spec.evaluate_pre_conditions(context, wf_def.decision_logic)
            if pre_failure:
                if len(pre_failure) == 4:
                    status, cond_name, final_summary, final_data = pre_failure
                else:
                    status, final_summary, final_data = pre_failure
                    cond_name = "Input Validation Gate"
                conditions_evaluated.append(ConditionEvaluation(
                    condition_name=cond_name,
                    rule_expression=wf_def.decision_logic,
                    outcome=False,
                    explanation=final_summary
                ))
            else:
                # 5. Generic Ordered Step Execution Loop
                for step in spec.executable_steps:
                    step_inputs = context.resolve_inputs(step.input_mappings)

                    t_step = time.time()
                    step_output = tool_registry.execute(step.tool_name, **step_inputs)
                    step_duration = round(time.time() - t_step, 4)

                    if step.output_variable:
                        context.set(step.output_variable, step_output)

                    summary_str = step.summary_template or f"Executed step '{step.step_name}'."
                    steps_executed.append(StepResult(
                        step_number=step.step_number,
                        step_name=step.step_name,
                        status="SUCCESS",
                        tool_name=step.tool_name,
                        tool_input=step_inputs,
                        tool_output_summary=summary_str,
                        duration_seconds=step_duration
                    ))
                    tools_invoked.append(step.tool_name)

                # 6. Deterministic Decision Rule Evaluation
                if spec.decision_evaluator:
                    eval_res = spec.decision_evaluator(context)
                    if isinstance(eval_res, tuple) and len(eval_res) == 4:
                        outcome, condition_name, explanation, rule_status = eval_res
                    elif isinstance(eval_res, tuple) and len(eval_res) == 3:
                        outcome, explanation, rule_status = eval_res
                        condition_name = f"{wf_def.workflow_name} Decision Gate"
                    else:
                        outcome = bool(eval_res)
                        condition_name = f"{wf_def.workflow_name} Decision Gate"
                        explanation = str(eval_res)
                        rule_status = "SUCCESS"

                    conditions_evaluated.append(ConditionEvaluation(
                        condition_name=condition_name,
                        rule_expression=wf_def.decision_logic,
                        outcome=outcome,
                        explanation=explanation
                    ))
                    if rule_status != "SUCCESS":
                        status = rule_status

                # 7. Summary & Data Formatting
                final_summary = spec.summary_renderer(context) if spec.summary_renderer else f"Completed {wf_def.workflow_name}."
                final_data = spec.data_extractor(context) if spec.data_extractor else context.state

        except Exception as e:
            logger.error(f"Execution error in workflow {wf_def.workflow_id}: {e}", exc_info=True)
            status = "FAILED"
            final_data = None
            final_summary = f"Execution error occurred while processing workflow {wf_def.workflow_id}: {str(e)}"
            err_msg = str(e)

        duration = round(time.time() - start_time, 3)

        return WorkflowExecutionResult(
            execution_id=exec_id,
            user_request=user_request,
            selected_workflow_id=wf_def.workflow_id,
            selected_workflow_name=wf_def.workflow_name,
            selection_confidence=selection.confidence,
            selection_reasoning=selection.reasoning,
            status=status,
            steps_executed=steps_executed,
            conditions_evaluated=conditions_evaluated,
            tools_invoked=list(set(tools_invoked)),
            final_result_data=final_data,
            final_summary=final_summary,
            duration_seconds=duration,
            error_message=err_msg
        )


# Global singleton engine
workflow_engine = WorkflowEngine()
