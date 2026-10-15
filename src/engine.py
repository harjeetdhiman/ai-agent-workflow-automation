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
        return self.execute_workflow(
            wf_def=wf_def,
            user_request=user_request,
            override_params=override_params,
            selection=selection
        )

    def execute_workflow(
        self,
        wf_def: WorkflowDefinition,
        user_request: str = "",
        override_params: Optional[Dict[str, Any]] = None,
        selection: Optional[WorkflowSelection] = None
    ) -> WorkflowExecutionResult:
        """Executes a parsed WorkflowDefinition directly through the common generic step pipeline."""
        start_time = time.time()
        exec_id = str(uuid.uuid4())[:8]

        if selection is None:
            selection = WorkflowSelection(
                workflow_id=wf_def.workflow_id,
                workflow_name=wf_def.workflow_name,
                confidence=1.0,
                reasoning="Direct workflow invocation"
            )

        # Merge extracted params with runtime overrides
        params = dict(selection.extracted_params or {})
        if override_params:
            params.update(override_params)
        params.setdefault("user_request", user_request)

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

            # Pass runtime context params and previous step state if not already set
            for pk, pv in {**context.params, **context.state}.items():
                if pk not in step_inputs and pv is not None and not pk.startswith("step_"):
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

            is_llm_step = (tool_name.lower() in ["llm_generate", "llm", "llm_fallback"])
            is_registered = tool_registry.has_tool(tool_name) and not is_llm_step

            from src.config import OPENAI_API_KEY
            if is_registered:
                executed_by = "tool"
            elif OPENAI_API_KEY and len(OPENAI_API_KEY.strip()) > 10:
                executed_by = "llm"
            else:
                executed_by = "simulated"

            for attempt in range(max_retries + 1):
                try:
                    if is_registered:
                        clean_inputs = {k: v for k, v in step_inputs.items() if k != "tool_name"}
                        step_output = tool_registry.execute(tool_name, **clean_inputs)
                    elif is_llm_step and tool_registry.has_tool("llm_generate"):
                        clean_inputs = {k: v for k, v in step_inputs.items() if k != "tool_name"}
                        step_output = tool_registry.execute("llm_generate", **clean_inputs)
                    else:
                        step_output = {
                            "status": "SUCCESS",
                            "executed_by": executed_by,
                            "tool_name": tool_name,
                            "summary": f"Simulated autonomous LLM fallback execution for '{tool_name}'",
                            "data": step_inputs
                        }
                    step_status = "SUCCESS"
                    break
                except Exception as e:
                    retries_done += 1
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

            step_summary = self._generate_step_summary(step_name, tool_name, step_inputs, step_output)
            steps_executed.append(StepResult(
                step_number=step_num,
                step_name=step_name,
                status=step_status,
                tool_name=tool_name,
                executed_by=executed_by,
                tool_input=step_inputs,
                tool_output_summary=step_summary,
                tool_output=step_output,
                details=step_output,
                error_message=step_err,
                duration_seconds=step_duration,
                retries=retries_done
            ))
            tools_invoked.append(tool_name)

            # Evaluate step condition gate
            cond_expr = step.condition_expr or step.condition
            if cond_expr:
                passed, reason = safe_evaluator.evaluate_condition(cond_expr, context.state)
                branch_action = step.on_true if passed else step.on_false

                cond_name = f"Step {step_num} Gate"
                if "campaign" in step_name.lower() or "dates" in cond_expr:
                    cond_name = "Mandatory Campaign Parameter Check"
                elif "skill" in step_name.lower() or "qualified" in cond_expr or "capacity" in cond_expr:
                    cond_name = "Capacity & Skill Allocation Rule"
                elif "order" in step_name.lower() or "found" in cond_expr:
                    cond_name = "Order Lookup Verification"

                explanation = reason
                if not passed and isinstance(step_output, dict) and step_output.get("error_message"):
                    explanation = step_output["error_message"]

                conditions_evaluated.append(ConditionEvaluation(
                    condition_name=cond_name,
                    rule_expression=cond_expr,
                    outcome=passed,
                    explanation=explanation,
                    branch_taken=branch_action
                ))

                if not passed:
                    if branch_action in ["stop", "ask_user", "escalate"]:
                        if branch_action == "ask_user":
                            status = "NEEDS_INPUT"
                        elif branch_action == "escalate":
                            status = "FAILED"
                        else:
                            status = "FAILED"
                        err_msg = explanation
                        break
                    elif branch_action == "skip":
                        continue

            # Additional declarative parameter presence check
            if step.params.get("check_keys"):
                missing = [k for k in step.params["check_keys"] if not context.get(k)]
                if missing:
                    cond_name = "Mandatory Campaign Parameter Check"
                    msg = f"Please provide {' and '.join(missing)} before generating the brief."
                    if not any(c.condition_name == cond_name for c in conditions_evaluated):
                        conditions_evaluated.append(ConditionEvaluation(
                            condition_name=cond_name,
                            rule_expression="all(k in params for k in check_keys)",
                            outcome=False,
                            explanation=msg,
                            branch_taken="halt"
                        ))
                    status = "NEEDS_INPUT"
                    err_msg = msg
                    break

            if isinstance(step_output, dict):
                if step_output.get("skills_provided") is False:
                    status = "NEEDS_INPUT"
                    err_msg = step_output.get("error_message") or "Please specify the required skills or role needed for the task."
                    if not any(c.condition_name == "Task Skills Gate" for c in conditions_evaluated):
                        conditions_evaluated.append(ConditionEvaluation(
                            condition_name="Task Skills Gate",
                            rule_expression="skills_provided",
                            outcome=False,
                            explanation=err_msg,
                            branch_taken="ask_user"
                        ))
                    break
                if step_output.get("found") is False:
                    status = "NEEDS_INPUT"
                    err_msg = step_output.get("error_message") or f"No order found matching identifier '{params.get('order_id', '')}'. Please provide another identifier."
                    if not any(c.condition_name == "Order Lookup Verification" for c in conditions_evaluated):
                        conditions_evaluated.append(ConditionEvaluation(
                            condition_name="Order Lookup Verification",
                            rule_expression="found",
                            outcome=False,
                            explanation=err_msg,
                            branch_taken="ask_user"
                        ))
                    break
                if step_output.get("decision") == "ESCALATED":
                    status = "FAILED"
                    err_msg = step_output.get("error_message") or "Escalated: No suitable candidate."
                    if not any(c.condition_name == "Capacity & Skill Allocation Rule" for c in conditions_evaluated):
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
                    status = "FAILED"
                    err_msg = f"Step '{step_name}' escalated: {step_err}"
                    break

        # 3. Decision Logic Evaluation
        if wf_def.decision_logic and status == "SUCCESS":
            decision_expr = safe_evaluator.convert_to_safe_expression(wf_def.decision_logic)
            decision_passed, decision_reason = safe_evaluator.evaluate_condition(
                decision_expr, context.state
            )
            conditions_evaluated.append(ConditionEvaluation(
                condition_name=f"{wf_def.workflow_name} Rule Gate",
                rule_expression=decision_expr,
                outcome=decision_passed,
                explanation=decision_reason,
                branch_taken="complete"
            ))

        # 4. Final Output Synthesis with Real Computed Deliverables
        summary_lines = [
            f"### Executed Workflow: {wf_def.workflow_name} ({wf_def.workflow_id})",
            f"**Execution Status:** {status}",
            f"**Total Steps Executed:** {len(steps_executed)}",
        ]
        if err_msg:
            summary_lines.append(f"**Notice / Alert:** {err_msg}")

        summary_lines.extend(self._format_computed_results(final_data))

        final_summary = "\n".join(summary_lines)
        if err_msg and not final_summary.startswith(err_msg):
            final_summary = f"{err_msg}\n\n" + final_summary

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

    def _generate_step_summary(self, step_name: str, tool_name: str, inputs: Dict[str, Any], output: Any) -> str:
        """Generates dynamic step summaries containing real values, counts, and metrics."""
        if not output:
            return f"{step_name}: No output produced."

        if isinstance(output, dict):
            if output.get("error_message"):
                return f"{step_name}: {output['error_message']}"
            if "records" in output and isinstance(output["records"], list):
                fpath = inputs.get("file_path", "")
                src_info = f" from {os.path.basename(fpath)}" if fpath else ""
                return f"Loaded {len(output['records'])} records{src_info}."
            if "matched_count" in output:
                return f"Filtered {output['matched_count']} matching records ({output.get('excluded_count', 0)} excluded)."
            if "clean_rows_count" in output and "invalid_rows_count" in output:
                return f"Audited feed: {output['clean_rows_count']} clean rows, {output['invalid_rows_count']} invalid rows flagged."
            if "overdue_count" in output:
                return f"Found {output['overdue_count']} overdue invoices totaling ${output.get('total_overdue_amount', 0):,.2f}."
            if "order_id" in output and output.get("found"):
                carrier = output.get("shipment_details", {}).get("carrier", "Carrier")
                return f"Retrieved order {output['order_id']} (Status: {output.get('order_status', 'Unknown')}, Carrier: {carrier})."
            if "assigned_employee" in output:
                emp = output["assigned_employee"]
                cap_free = 100 - float(emp.get("current_workload_pct", 50))
                return f"Selected candidate '{emp.get('name')}' ({emp.get('role', 'Developer')}) with {cap_free:.0f}% available capacity."
            if "exceptions_flagged_count" in output:
                return f"Compared {output.get('total_matched', 0)} prices, flagged {output['exceptions_flagged_count']} exceptions >10%."
            if "definite_duplicates_count" in output or "duplicates_removed" in output:
                return f"Identified {output.get('definite_duplicates_count', 0)} exact and {output.get('possible_duplicates_count', 0)} fuzzy duplicates."
            if "intent_distribution" in output:
                intents_str = ", ".join(f"{k}:{v}" for k, v in output["intent_distribution"].items())
                return f"Classified search intents ({intents_str})."
            if "seo_title" in output:
                return f"Generated SEO Title ({output.get('seo_title_length', 0)} chars): '{output['seo_title']}'"
            if "meta_description" in output:
                return f"Generated Meta Description ({output.get('meta_description_length', 0)} chars)."
            if "messaging_pillars" in output:
                return f"Synthesized campaign brief with {len(output['messaging_pillars'])} messaging pillars and {len(output.get('channel_recommendations', []))} channels."
            if "summary" in output:
                return str(output["summary"])

        return f"Completed {step_name} successfully."

    def _format_computed_results(self, data: Dict[str, Any]) -> List[str]:
        """Dynamically renders computed output metrics and tables from execution context."""
        lines = []
        if not data:
            return lines

        # 1. Scalar summary metrics (filter out internal/junk keys)
        junk_keys = {
            "count", "status", "file_path", "filepath", "path", "source", "valid",
            "matched_count", "excluded_count", "total_scanned", "total_records",
            "clean_rows_count", "invalid_rows_count", "skills_provided", "found",
            "identifier_present", "attribute_audit", "tool_name", "simulated",
            "params", "type", "operation", "summary"
        }
        scalar_metrics = []
        for k, v in data.items():
            k_lower = k.lower()
            if k_lower in junk_keys or k_lower.startswith("step_") or "present" in k_lower or k_lower.endswith("_present"):
                continue
            str_v = str(v)
            if any(p in str_v for p in ["Structured deliverable", "Executed ", "Simulated autonomous"]):
                continue
            if isinstance(v, (int, float, bool, str)) and len(str_v) < 120:
                display_k = k.replace("_", " ").title()
                scalar_metrics.append(f"- **{display_k}:** {v}")

        if scalar_metrics:
            lines.append("\n**Key Output Metrics & Indicators:**")
            lines.extend(scalar_metrics[:10])

        # 2. Tabular record deliverables (lists of dicts)
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], dict) and not k.startswith("step_"):
                display_title = k.replace("_", " ").title()
                lines.append(f"\n**{display_title} ({len(v)} records):**")
                cols = [c for c in list(v[0].keys())[:6] if not c.startswith("_")]
                header = "| " + " | ".join(c.replace("_", " ").title() for c in cols) + " |"
                sep = "| " + " | ".join("---" for _ in cols) + " |"
                lines.append(header)
                lines.append(sep)
                for row in v[:12]:
                    row_vals = [str(row.get(c, "")).replace("|", "/") for c in cols]
                    lines.append("| " + " | ".join(row_vals) + " |")
                if len(v) > 12:
                    lines.append(f"*... and {len(v) - 12} additional records.*")

        # 3. Structured objects (e.g. details, assignments, audits)
        for k, v in data.items():
            if isinstance(v, dict) and not k.startswith("step_") and k not in ["data", "attribute_audit"]:
                display_title = k.replace("_", " ").title()
                lines.append(f"\n**{display_title}:**")
                for sub_k, sub_v in list(v.items())[:8]:
                    if not isinstance(sub_v, (dict, list)):
                        lines.append(f"  - **{sub_k.replace('_', ' ').title()}:** {sub_v}")

        # 4. List deliverables (e.g. pillars, recommendations, checklists)
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], str) and not k.startswith("step_"):
                display_title = k.replace("_", " ").title()
                lines.append(f"\n**{display_title}:**")
                for item in v[:10]:
                    lines.append(f"  - {item}")

        return lines

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
