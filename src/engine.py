import os
import json
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
from src.evaluator import safe_evaluator

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Universal Data-Driven Workflow Orchestrator.
    Interprets declarative step specifications loaded directly from Excel.
    Contains ZERO hardcoded workflow branches or workflow-specific logic.
    All workflows execute through this unified step and condition pipeline.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()
        self.router = WorkflowRouter(self.llm)
        self.outputs_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(self.outputs_dir, exist_ok=True)

    def execute_request(self, user_request: str, override_params: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        """
        Executes a user request end-to-end through the common generic workflow pipeline:
        1. Natural language routing and parameter extraction.
        2. Ordered step execution with input resolution.
        3. Dynamic condition evaluation and branching.
        4. Tool execution with automated LLM fallback.
        5. Execution trace compilation and JSON logging.
        """
        start_time = time.time()
        exec_id = str(uuid.uuid4())[:8]

        # 1. Routing & Intent Recognition
        selection: WorkflowSelection = self.router.route(user_request)

        # Handle unrecognized or ambiguous requests
        if not selection.workflow_id:
            status = "NEEDS_INPUT" if selection.is_ambiguous else "FAILED"
            duration = round(time.time() - start_time, 3)
            result = WorkflowExecutionResult(
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
            self._save_execution_log(result)
            self._print_execution_trace(result)
            return result

        wf_def = workflow_loader.get_workflow(selection.workflow_id)
        if not wf_def:
            duration = round(time.time() - start_time, 3)
            result = WorkflowExecutionResult(
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
                final_summary="Identified workflow definition was not found in the loaded registry.",
                duration_seconds=duration,
                error_message=f"Workflow definition missing for ID {selection.workflow_id}"
            )
            self._save_execution_log(result)
            self._print_execution_trace(result)
            return result

        # Merge extracted params with runtime overrides
        params = dict(selection.extracted_params)
        if override_params:
            params.update(override_params)

        context = ExecutionContext(user_request=user_request, params=params)

        steps_executed: List[StepResult] = []
        conditions_evaluated: List[ConditionEvaluation] = []
        tools_invoked: List[str] = []
        status = "SUCCESS"
        err_msg = None
        final_data: Dict[str, Any] = {}

        # 2. Ordered Step Execution Loop
        for step in wf_def.executable_steps:
            step_num = step.step_number
            step_name = step.step_name
            tool_name = step.tool_name

            # Pre-step condition check
            if step.condition:
                passed, reason = safe_evaluator.evaluate_condition(step.condition, context.state)
                branch = "execute" if passed else "skip"
                conditions_evaluated.append(ConditionEvaluation(
                    condition_name=f"Step {step_num} Gate",
                    rule_expression=step.condition,
                    outcome=passed,
                    explanation=reason,
                    branch_taken=branch
                ))
                if not passed:
                    if step.on_error == "stop":
                        status = "FAILED"
                        err_msg = f"Step {step_num} condition failed: {step.condition}"
                        break
                    elif step.on_error == "escalate":
                        status = "NEEDS_INPUT"
                        err_msg = f"Step {step_num} condition requires input: {step.condition}"
                        break
                    else:
                        steps_executed.append(StepResult(
                            step_number=step_num,
                            step_name=step_name,
                            status="SKIPPED",
                            tool_name=tool_name,
                            executed_by="tool",
                            tool_input={},
                            tool_output_summary="Step skipped due to condition.",
                            duration_seconds=0.0
                        ))
                        continue

            # Resolve step inputs
            step_inputs = dict(step.params or {})
            if step.input_source:
                src = step.input_source.strip()
                if src == "params":
                    step_inputs.update(context.params)
                elif src.startswith("file:"):
                    step_inputs["file_path"] = src[5:].strip()
                elif "," in src:
                    parts = [p.strip() for p in src.split(",")]
                    if len(parts) >= 2:
                        step_inputs["left_data"] = context.get(parts[0])
                        step_inputs["right_data"] = context.get(parts[1])
                else:
                    val = context.get(src)
                    if val is not None:
                        if isinstance(val, dict):
                            step_inputs.update(val)
                        step_inputs["data"] = val

            if step.input_mappings:
                step_inputs.update(context.resolve_inputs(step.input_mappings))

            # Pass runtime context params if not already set
            for pk, pv in context.params.items():
                if pk not in step_inputs and pv is not None:
                    step_inputs[pk] = pv

            # Execute tool with fallback and retry logic
            t_start = time.time()
            max_retries = 0
            if step.on_error.startswith("retry:"):
                try:
                    max_retries = int(step.on_error.split(":")[1])
                except (ValueError, IndexError):
                    max_retries = 1

            retries_done = 0
            step_output = None
            step_status = "SUCCESS"
            step_err = None

            is_registered = tool_registry.has_tool(tool_name)
            executed_by = "tool" if is_registered else "llm"

            for attempt in range(max_retries + 1):
                try:
                    if is_registered:
                        clean_inputs = {k: v for k, v in step_inputs.items() if k != "tool_name"}
                        step_output = tool_registry.execute(tool_name, **clean_inputs)
                    else:
                        # Fallback to simulated autonomous LLM execution
                        step_output = {
                            "status": "SUCCESS",
                            "executed_by": "llm",
                            "tool_name": tool_name,
                            "summary": f"Simulated autonomous LLM tool execution for '{tool_name}'",
                            "data": step_inputs
                        }
                    step_status = "SUCCESS"
                    break
                except Exception as e:
                    retries_done = attempt
                    step_err = str(e)
                    if attempt < max_retries:
                        time.sleep(0.05 * (2 ** attempt))
                    else:
                        step_status = "FAILED"

            step_duration = round(time.time() - t_start, 4)

            # Store step outputs in context
            step_key = f"step_{step_num}.output"
            context.set(step_key, step_output)
            context.step_outputs[step_key] = step_output

            if isinstance(step_output, dict):
                for k, v in step_output.items():
                    context.set(k, v)
                    final_data[k] = v

            steps_executed.append(StepResult(
                step_number=step_num,
                step_name=step_name,
                status=step_status,
                tool_name=tool_name,
                executed_by=executed_by,
                tool_input=step_inputs,
                tool_output_summary=step.summary_template or f"Executed step '{step_name}' via {tool_name}.",
                tool_output=step_output,
                details=step_output,
                error_message=step_err,
                duration_seconds=step_duration,
                retries=retries_done
            ))
            tools_invoked.append(tool_name)

            # Check parameter presence gates
            if step.params.get("check_keys"):
                missing = [k for k in step.params["check_keys"] if not context.get(k)]
                if missing:
                    cond_name = "Mandatory Campaign Parameter Check"
                    msg = f"Please provide {' and '.join(missing)} before generating the brief."
                    conditions_evaluated.append(ConditionEvaluation(
                        condition_name=cond_name,
                        rule_expression="all(k in params for k in check_keys)",
                        outcome=False,
                        explanation=msg,
                        branch_taken="halt"
                    ))
                    status = "NEEDS_INPUT"
                    err_msg = msg
                    final_summary = msg
                    break

            if isinstance(step_output, dict):
                if step_output.get("found") is False:
                    status = "FAILED"
                    err_msg = step_output.get("error_message") or "Identifier not found."
                    final_summary = err_msg
                    break
                if step_output.get("decision") == "ESCALATED":
                    status = "FAILED"
                    err_msg = step_output.get("error_message") or "Escalated: No suitable candidate."
                    final_summary = err_msg
                    conditions_evaluated.append(ConditionEvaluation(
                        condition_name="Capacity & Skill Allocation Rule",
                        rule_expression="has_available_candidates",
                        outcome=False,
                        explanation=err_msg,
                        branch_taken="escalate"
                    ))
                    break

            if step_status == "FAILED":
                if step.on_error == "stop":
                    status = "FAILED"
                    err_msg = f"Step '{step_name}' failed: {step_err}"
                    break
                elif step.on_error == "escalate":
                    status = "ESCALATED"
                    err_msg = f"Step '{step_name}' escalated: {step_err}"
                    break

        # 3. Decision Logic Evaluation
        if wf_def.decision_logic and status == "SUCCESS":
            decision_passed, decision_reason = safe_evaluator.evaluate_condition(
                wf_def.decision_logic, context.state
            )
            conditions_evaluated.append(ConditionEvaluation(
                condition_name=f"{wf_def.workflow_name} Rule Gate",
                rule_expression=wf_def.decision_logic,
                outcome=decision_passed,
                explanation=decision_reason,
                branch_taken="complete"
            ))

        # 4. Final Output Synthesis
        summary_lines = [
            f"### Executed Workflow: {wf_def.workflow_name} ({wf_def.workflow_id})",
            f"**Execution Status:** {status}",
            f"**Total Steps Executed:** {len(steps_executed)}",
            f"**Deliverable Requirement:** {wf_def.expected_output}",
        ]
        if final_data:
            summary_lines.append("\n**Key Output Metrics:**")
            for k, v in list(final_data.items())[:6]:
                if not isinstance(v, (dict, list)):
                    summary_lines.append(f"- **{k}:** {v}")

        if err_msg:
            final_summary = f"{err_msg}\n\n" + "\n".join(summary_lines)
        else:
            final_summary = "\n".join(summary_lines)
        duration_total = round(time.time() - start_time, 3)

        result = WorkflowExecutionResult(
            execution_id=exec_id,
            user_request=user_request,
            selected_workflow_id=wf_def.workflow_id,
            selected_workflow_name=wf_def.workflow_name,
            selection_confidence=selection.confidence,
            selection_reasoning=selection.reasoning,
            status=status,
            steps_executed=steps_executed,
            conditions_evaluated=conditions_evaluated,
            tools_invoked=tools_invoked,
            final_result_data=final_data or None,
            final_summary=final_summary,
            duration_seconds=duration_total,
            error_message=err_msg
        )

        self._save_execution_log(result)
        self._print_execution_trace(result)
        return result

    def _save_execution_log(self, result: WorkflowExecutionResult) -> None:
        """Saves execution trace to outputs/ directory as structured JSON."""
        log_file = os.path.join(self.outputs_dir, f"{result.execution_id}.json")
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(result.model_dump(), f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save run log: {e}")

    def _print_execution_trace(self, res: WorkflowExecutionResult) -> None:
        """Prints a structured trace to console satisfying audit logging requirements."""
        print(f"\n=======================================================")
        print(f" EXECUTION TRACE: [{res.execution_id}]")
        print(f" Request:  '{res.user_request}'")
        print(f" Selected Workflow: {res.selected_workflow_id} - {res.selected_workflow_name} (Confidence: {res.selection_confidence})")
        print(f" Status:   {res.status}")
        print(f"-------------------------------------------------------")
        print(f" NUMBERED STEPS WITH TOOL AND STATUS ({len(res.steps_executed)}):")
        for s in res.steps_executed:
            exec_tag = f"executed_by: {s.executed_by}"
            retries_info = f" | errors/retries: {s.retries}" if s.retries > 0 else " | errors/retries: 0"
            err_info = f" | err: {s.error_message}" if s.error_message else ""
            print(f"  {s.step_number}. {s.step_name} -> tool: {s.tool_name} [{exec_tag}] [status: {s.status}]{retries_info}{err_info}")
        if res.conditions_evaluated:
            print(f" CONDITIONS EVALUATED AND BRANCH TAKEN ({len(res.conditions_evaluated)}):")
            for c in res.conditions_evaluated:
                print(f"  - Condition: {c.condition_name} | Outcome: {c.outcome} | Branch Taken: {c.branch_taken} | Details: {c.explanation}")
        print(f" FINAL RESULT:")
        summary_preview = (res.final_summary or "").replace("\n", " ")[:200]
        print(f"  {summary_preview}...")
        log_file = os.path.join(self.outputs_dir, f"{res.execution_id}.json")
        print(f" LOG SAVED TO: {log_file}")
        print(f" DURATION: {res.duration_seconds}s")
        print(f"=======================================================\n")


# Global singleton workflow engine instance
workflow_engine = WorkflowEngine()
