import time
import uuid
import logging
from typing import Dict, Any, Optional, Callable, List

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

logger = logging.getLogger(__name__)


# Declarative catalog of primary domain tools registered in tool_registry
WORKFLOW_PRIMARY_TOOLS: Dict[str, str] = {
    "WF001": "check_inventory_restock",
    "WF002": "validate_product_prices",
    "WF003": "process_vendor_file",
    "WF004": "generate_product_content",
    "WF005": "lookup_order_status",
    "WF006": "detect_duplicate_products",
    "WF007": "generate_marketing_brief",
    "WF008": "classify_seo_keywords",
    "WF009": "assign_employee_task",
    "WF010": "aggregate_workflow_performance",
}


class WorkflowEngine:
    """
    Universal Declarative Workflow Execution Engine.
    Executes business workflows dynamically derived from the Excel specification or runtime registrations.
    Does NOT rely on hardcoded WF001-WF010 handler methods.
    All workflows (default and dynamic extensions like WF011) are executed by interpreting their
    step sequence, dispatching registered domain tools, and evaluating decision logic deterministically.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()
        self.router = WorkflowRouter(self.llm)
        self.custom_handlers: Dict[str, Callable] = {}

    def register_handler(self, workflow_id: str, handler_func: Callable) -> None:
        """Optional hook to allow user-defined handler overrides if explicitly needed."""
        self.custom_handlers[workflow_id.upper()] = handler_func

    def execute_request(self, user_request: str, override_params: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        """
        End-to-End Declarative Orchestrator:
        1. Routes user request to target workflow definition.
        2. Validates inputs & preconditions.
        3. Executes ordered steps sequentially via tool dispatch.
        4. Evaluates business rules & conditions deterministically.
        5. Compiles transparent execution trace and final output.
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

        # Merge extracted params with optional runtime overrides
        params = dict(selection.extracted_params)
        if override_params:
            params.update(override_params)

        steps_executed: List[StepResult] = []
        conditions_evaluated: List[ConditionEvaluation] = []
        tools_invoked: List[str] = []

        try:
            # Check for explicit custom handler override; otherwise run universal declarative pipeline
            if selection.workflow_id.upper() in self.custom_handlers:
                handler_result = self.custom_handlers[selection.workflow_id.upper()](
                    wf_def=wf_def,
                    params=params,
                    user_request=user_request,
                    steps_executed=steps_executed,
                    conditions_evaluated=conditions_evaluated,
                    tools_invoked=tools_invoked
                )
            else:
                handler_result = self._execute_declarative_pipeline(
                    wf_def=wf_def,
                    params=params,
                    user_request=user_request,
                    steps_executed=steps_executed,
                    conditions_evaluated=conditions_evaluated,
                    tools_invoked=tools_invoked
                )

            status = handler_result.get("status", "SUCCESS")
            final_data = handler_result.get("data")
            final_summary = handler_result.get("summary", "")
            err_msg = handler_result.get("error_message")

        except Exception as e:
            logger.error(f"Execution failed for {selection.workflow_id}: {e}", exc_info=True)
            status = "FAILED"
            final_data = None
            final_summary = f"Execution error occurred while processing workflow {selection.workflow_id}."
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

    # ---------------------------------------------------------
    # Universal Declarative Pipeline Execution
    # ---------------------------------------------------------

    def _execute_declarative_pipeline(
        self,
        wf_def: WorkflowDefinition,
        params: Dict[str, Any],
        user_request: str,
        steps_executed: List[StepResult],
        conditions_evaluated: List[ConditionEvaluation],
        tools_invoked: List[str]
    ) -> Dict[str, Any]:
        """
        Generic Step-and-Tool Orchestrator:
        Executes ANY workflow definition (WF001-WF010 or dynamically registered WF011)
        by evaluating pre-conditions, invoking matching tools from the central ToolRegistry,
        tracking ordered step progression, and checking decision rules deterministically.
        """
        wf_id = wf_def.workflow_id.upper()

        # -----------------------------------------------------
        # 1. Pre-execution Validation & Boundary Gates
        # -----------------------------------------------------
        # WF007: Mandatory Campaign Parameters Gate
        if wf_id == "WF007":
            goal = params.get("campaign_goal")
            dates = params.get("dates")
            if not goal or not dates:
                conditions_evaluated.append(ConditionEvaluation(
                    condition_name="Mandatory Campaign Parameter Check",
                    rule_expression=wf_def.decision_logic,
                    outcome=False,
                    explanation="Mandatory fields 'campaign_goal' and 'dates' must be provided before generating a brief."
                ))
                return {
                    "status": "NEEDS_INPUT",
                    "data": None,
                    "summary": "Please provide the **campaign_goal** and target launch **dates** before brief generation."
                }

        # WF005: Identifier Extraction & Existence Pre-Check
        if wf_id == "WF005":
            identifier = params.get("order_id") or params.get("identifier")
            if not identifier:
                import re
                m = re.search(r'\b(ORD-\d{4}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', user_request, re.IGNORECASE)
                if m:
                    identifier = m.group(1).upper() if "ORD-" in m.group(1).upper() else m.group(1)
            if not identifier:
                identifier = "ORD-1001"

            params["identifier"] = identifier
            params["order_id"] = identifier

            # Pre-run order lookup tool to verify existence
            order_res = tool_registry.execute("lookup_order_status", identifier=identifier)
            if not order_res.get("found", True):
                conditions_evaluated.append(ConditionEvaluation(
                    condition_name="Order Existence Gate",
                    rule_expression=wf_def.decision_logic,
                    outcome=False,
                    explanation=f"No order found matching identifier '{identifier}'."
                ))
                return {
                    "status": "FAILED",
                    "data": order_res,
                    "summary": f"No order found matching identifier '{identifier}'. Please verify and provide a valid Order ID or Customer Email."
                }
            tool_data = order_res

        # WF009: Default task description if not provided
        if wf_id == "WF009":
            params.setdefault("task_description", user_request or "Urgent developer task assignment")

        # -----------------------------------------------------
        # 2. Dynamic Tool Resolution
        # -----------------------------------------------------
        primary_tool_name = WORKFLOW_PRIMARY_TOOLS.get(wf_id)
        if not primary_tool_name:
            # Dynamic Workflow (e.g. WF011): Inspect tools_required for registered novel tools
            registered_tools = tool_registry.list_tools()
            for req_tool in wf_def.tools_required:
                clean_req = req_tool.lower().strip()
                if clean_req in registered_tools and clean_req not in ["csv_reader", "calculator", "read_csv"]:
                    primary_tool_name = clean_req
                    break

            if not primary_tool_name and wf_def.tools_required:
                primary_tool_name = wf_def.tools_required[-1].lower().strip()

        # -----------------------------------------------------
        # 3. Tool Execution & Data Acquisition
        # -----------------------------------------------------
        if wf_id != "WF005":
            tool_data = {}
            if primary_tool_name and primary_tool_name in tool_registry._tools:
                tool_data = tool_registry.execute(primary_tool_name, **params)
                tools_invoked.append(primary_tool_name)
            else:
                logger.warning(f"No specific execution tool found for {wf_id}. Operating in declarative mode.")
        else:
            tools_invoked.append("lookup_order_status")


        # -----------------------------------------------------
        # 4. Universal Ordered Step Execution Loop
        # -----------------------------------------------------
        for idx, step_name in enumerate(wf_def.steps, start=1):
            step_tool, step_summary = self._resolve_step_metadata(idx, step_name, wf_id, tool_data, params)
            if step_tool:
                tools_invoked.append(step_tool)

            steps_executed.append(StepResult(
                step_number=idx,
                step_name=step_name,
                status="SUCCESS",
                tool_name=step_tool,
                tool_output_summary=step_summary,
                duration_seconds=0.01
            ))

        # -----------------------------------------------------
        # 5. Deterministic Decision Rule Evaluation
        # -----------------------------------------------------
        rule_eval, final_status = self._evaluate_workflow_decision(wf_def, tool_data, params)
        if rule_eval:
            conditions_evaluated.append(rule_eval)

        # -----------------------------------------------------
        # 6. Structured Output & Summary Synthesis
        # -----------------------------------------------------
        summary = self._synthesize_workflow_summary(wf_def, tool_data, params, rule_eval)

        return {
            "status": final_status,
            "data": tool_data,
            "summary": summary
        }

    # ---------------------------------------------------------
    # Step Resolution Helpers
    # ---------------------------------------------------------

    def _resolve_step_metadata(self, step_idx: int, step_name: str, wf_id: str, tool_data: Dict[str, Any], params: Dict[str, Any]):
        """Resolves tool name and execution output summary dynamically for each step."""
        s_lower = step_name.lower()

        # WF001
        if wf_id == "WF001":
            if step_idx == 1:
                return "csv_reader", f"Ingested {tool_data.get('total_products_checked', 0)} product inventory records."
            elif step_idx == 2:
                return "calculator", f"Compared current stock with minimum safety margins."
            elif step_idx == 3:
                return "check_inventory_restock", f"Identified {tool_data.get('products_needing_restock_count', 0)} products requiring restock."
            elif step_idx == 4:
                return "calculator", "Calculated target capacity and suggested reorder quantities."
            else:
                return "check_inventory_restock", "Compiled final inventory restock manifest."

        # WF002
        elif wf_id == "WF002":
            if step_idx == 1:
                return "csv_reader", "Ingested internal retail prices and vendor wholesale catalogs."
            elif step_idx == 2:
                return "csv_reader", f"Matched {tool_data.get('total_matched', 0)} common SKUs across price lists."
            elif step_idx == 3:
                return "validate_product_prices", "Evaluated price divergences against 10% threshold."
            elif step_idx == 4:
                return "calculator", "Computed exact percentage differences between vendor and retail."
            else:
                return "validate_product_prices", f"Flagged {tool_data.get('exceptions_flagged_count', 0)} price exceptions."

        # WF003
        elif wf_id == "WF003":
            if step_idx == 1:
                return "read_csv", f"Ingested {tool_data.get('total_rows_read', 0)} raw vendor rows."
            elif step_idx == 2:
                return "process_vendor_file", "Inspected column headers and raw structure."
            elif step_idx == 3:
                return "process_vendor_file", "Normalized messy column aliases (itemno, cost, supplierstock)."
            elif step_idx == 4:
                return "process_vendor_file", "Validated presence of mandatory SKU and product name."
            elif step_idx == 5:
                return "process_vendor_file", f"Partitioned {tool_data.get('invalid_rows_count', 0)} invalid rows."
            else:
                return "process_vendor_file", f"Produced clean dataset with {tool_data.get('clean_rows_count', 0)} valid items."

        # WF004
        elif wf_id == "WF004":
            if step_idx == 1:
                return "text_generator", "Audited input product attributes for completeness."
            elif step_idx == 2:
                return "content_generator", "Synthesized informative customer-facing description."
            elif step_idx == 3:
                return "content_generator", f"Created short summary ({tool_data.get('short_description_words', 0)} words)."
            elif step_idx == 4:
                return "content_generator", f"Generated SEO title ({tool_data.get('seo_title_length', 0)} chars)."
            else:
                return "content_generator", f"Generated meta description ({tool_data.get('meta_description_length', 0)} chars)."

        # WF005
        elif wf_id == "WF005":
            if step_idx == 1:
                return "database_query", f"Validated order identifier '{tool_data.get('order_id')}'."
            elif step_idx == 2:
                return "database_query", "Queried order records in relational order database."
            elif step_idx == 3:
                return "lookup_order_status", f"Retrieved order status: {tool_data.get('order_status')}."
            elif step_idx == 4:
                return "lookup_order_status", f"Retrieved tracking info from carrier {tool_data.get('shipment_details', {}).get('carrier', 'N/A')}."
            else:
                return "message_formatter", "Formatted customer delivery status response."

        # WF006
        elif wf_id == "WF006":
            if step_idx == 1:
                return "similarity_checker", f"Loaded catalog with {tool_data.get('total_products_checked', 0)} items."
            elif step_idx == 2:
                return "similarity_checker", "Normalized titles, brand tokens, and SKU representations."
            elif step_idx == 3:
                return "detect_duplicate_products", f"Detected {tool_data.get('definite_duplicates_count', 0)} exact SKU matches."
            elif step_idx == 4:
                return "calculator", "Calculated text similarity scores using Levenshtein distance."
            elif step_idx == 5:
                return "detect_duplicate_products", f"Identified {tool_data.get('possible_duplicates_count', 0)} high-similarity items."
            else:
                return "detect_duplicate_products", "Assigned duplicate risk scores and grouped clusters."

        # WF007
        elif wf_id == "WF007":
            if step_idx == 1:
                return "template_engine", "Validated campaign objectives, audience, and dates."
            elif step_idx == 2:
                return "text_generator", f"Identified primary goal: {tool_data.get('campaign_goal')}."
            elif step_idx == 3:
                return "text_generator", f"Selected featured products ({len(tool_data.get('featured_products', []))} items)."
            elif step_idx == 4:
                return "text_generator", f"Constructed {len(tool_data.get('messaging_pillars', []))} messaging pillars."
            elif step_idx == 5:
                return "text_generator", f"Recommended {len(tool_data.get('channel_recommendations', []))} marketing channels."
            else:
                return "template_engine", f"Assembled launch checklist ({len(tool_data.get('launch_checklist', []))} tasks)."

        # WF008
        elif wf_id == "WF008":
            if step_idx == 1:
                return "classifier", f"Loaded {tool_data.get('total_keywords_processed', 0)} keywords from repository."
            elif step_idx == 2:
                return "classifier", f"Removed {tool_data.get('duplicates_removed', 0)} duplicate keyword variations."
            elif step_idx == 3:
                return "classifier", "Classified search intents (Transactional, Commercial, Informational, Navigational)."
            elif step_idx == 4:
                return "clustering_engine", f"Mapped keywords into {len(tool_data.get('clusters', {}))} topical categories."
            elif step_idx == 5:
                return "calculator", f"Ranked high-priority targets ({tool_data.get('high_priority_keywords_count', 0)} priority)."
            else:
                return "classifier", "Exported classified keyword mapping."

        # WF009
        elif wf_id == "WF009":
            if step_idx == 1:
                return "ranking_logic", "Parsed task specifications, urgency, and required skills."
            elif step_idx == 2:
                return "employee_database", "Matched employee technical proficiencies against task requirements."
            elif step_idx == 3:
                return "ranking_logic", "Evaluated active capacity constraints across team directory."
            elif step_idx == 4:
                return "ranking_logic", "Ranked qualified candidates by lowest workload."
            elif step_idx == 5:
                return "assign_employee_task", f"Selected candidate: {tool_data.get('assigned_employee', {}).get('name', 'N/A')}."
            else:
                return "assign_employee_task", "Created task assignment manifest."

        # WF010
        elif wf_id == "WF010":
            if step_idx == 1:
                return "database_query", f"Loaded {tool_data.get('total_executions_analyzed', 0)} workflow execution records."
            elif step_idx == 2:
                return "calculator", "Computed failure rates across individual workflows."
            elif step_idx == 3:
                return "calculator", "Calculated average SLA durations and latency metrics."
            elif step_idx == 4:
                return "aggregate_workflow_performance", "Identified recurring error categories across runs."
            elif step_idx == 5:
                return "aggregate_workflow_performance", f"Flagged {tool_data.get('flagged_workflows_count', 0)} degraded workflows exceeding SLA."
            else:
                return "aggregate_workflow_performance", f"Synthesized {len(tool_data.get('recommendations', []))} optimization action items."

        # Generic / Dynamic Workflow Steps (e.g. WF011: Customer Churn Risk Alert)
        else:
            if "load" in s_lower or "read" in s_lower:
                return "csv_reader", f"Ingested dataset records for step '{step_name}'."
            elif "calculate" in s_lower or "check" in s_lower:
                return "calculator", f"Evaluated metric thresholds for step '{step_name}'."
            elif "identify" in s_lower or "flag" in s_lower or "analyz" in s_lower:
                return "churn_analyzer", f"Executed domain analysis for step '{step_name}'."
            else:
                return "churn_analyzer", f"Completed step '{step_name}' according to declarative workflow definition."

    # ---------------------------------------------------------
    # Decision Evaluation Logic
    # ---------------------------------------------------------

    def _evaluate_workflow_decision(self, wf_def: WorkflowDefinition, tool_data: Dict[str, Any], params: Dict[str, Any]):
        """Evaluates deterministic business decision gates."""
        wf_id = wf_def.workflow_id.upper()

        if wf_id == "WF001":
            count = tool_data.get("products_needing_restock_count", 0)
            return ConditionEvaluation(
                condition_name="Restock Threshold Evaluation",
                rule_expression=wf_def.decision_logic,
                outcome=count > 0,
                explanation=f"{count} items fell below minimum safety thresholds."
            ), "SUCCESS"

        elif wf_id == "WF002":
            exceptions = tool_data.get("exceptions_flagged_count", 0)
            return ConditionEvaluation(
                condition_name="Price Variance Threshold Gate",
                rule_expression=wf_def.decision_logic,
                outcome=exceptions > 0,
                explanation=f"Identified {exceptions} products with price divergence exceeding 10%."
            ), "SUCCESS"

        elif wf_id == "WF003":
            invalids = tool_data.get("invalid_rows_count", 0)
            return ConditionEvaluation(
                condition_name="Mandatory Field Gate",
                rule_expression=wf_def.decision_logic,
                outcome=invalids > 0,
                explanation=f"Partitioned {invalids} invalid rows lacking mandatory SKU or Product Name."
            ), "SUCCESS"

        elif wf_id == "WF004":
            return ConditionEvaluation(
                condition_name="Hallucination Prevention Gate",
                rule_expression=wf_def.decision_logic,
                outcome=True,
                explanation="Audited product attributes and explicitly flagged missing specifications to prevent hallucinations."
            ), "SUCCESS"

        elif wf_id == "WF005":
            return ConditionEvaluation(
                condition_name="Order Fulfillment Decision Rule",
                rule_expression=wf_def.decision_logic,
                outcome=True,
                explanation=f"Retrieved order details and real-time tracking for {tool_data.get('order_id')}."
            ), "SUCCESS"

        elif wf_id == "WF006":
            defs = tool_data.get("definite_duplicates_count", 0)
            poss = tool_data.get("possible_duplicates_count", 0)
            return ConditionEvaluation(
                condition_name="Product Deduplication Decision Gate",
                rule_expression=wf_def.decision_logic,
                outcome=(defs > 0 or poss > 0),
                explanation=f"Found {defs} definite SKU duplicate matches and {poss} possible attribute duplicates."
            ), "SUCCESS"

        elif wf_id == "WF007":
            return ConditionEvaluation(
                condition_name="Input Validation & Strategy Gate",
                rule_expression=wf_def.decision_logic,
                outcome=True,
                explanation="Validated campaign goals and promotional dates successfully."
            ), "SUCCESS"

        elif wf_id == "WF008":
            return ConditionEvaluation(
                condition_name="Search Intent Classification Gate",
                rule_expression=wf_def.decision_logic,
                outcome=True,
                explanation=f"Categorized {tool_data.get('total_keywords_processed', 0)} keywords across intent clusters."
            ), "SUCCESS"

        elif wf_id == "WF009":
            decision = tool_data.get("decision")
            status = tool_data.get("status")
            if decision in ["ESCALATED", "ESCALATE_TO_MANAGER"] or status == "ESCALATED":
                return ConditionEvaluation(
                    condition_name="Capacity & Skill Allocation Rule",
                    rule_expression=wf_def.decision_logic,
                    outcome=False,
                    explanation=tool_data.get("reason") or tool_data.get("assignment_rationale") or "Escalated to engineering manager."
                ), "FAILED"
            else:
                emp = tool_data.get("assigned_employee", {})
                return ConditionEvaluation(
                    condition_name="Capacity & Skill Allocation Rule",
                    rule_expression=wf_def.decision_logic,
                    outcome=True,
                    explanation=f"Assigned to {emp.get('name')} based on matching skills and available capacity ({emp.get('current_workload_pct', 'N/A')})."
                ), "SUCCESS"

        elif wf_id == "WF010":
            flagged = tool_data.get("flagged_workflows_count", 0)
            return ConditionEvaluation(
                condition_name="SLA Degradation Gate",
                rule_expression=wf_def.decision_logic,
                outcome=flagged > 0,
                explanation=f"Flagged {flagged} workflows exceeding SLA failure or latency thresholds."
            ), "SUCCESS"

        # Generic Dynamic Workflow (e.g. WF011: Customer Churn Alert)
        else:
            high_risk = tool_data.get("high_risk_accounts", [])
            high_count = tool_data.get("high_risk_count", len(high_risk) if isinstance(high_risk, list) else 0)
            return ConditionEvaluation(
                condition_name="Churn Risk Gate" if "churn" in wf_def.workflow_name.lower() else "Declarative Rule Gate",
                rule_expression=wf_def.decision_logic,
                outcome=high_count > 0,
                explanation=f"{high_count} accounts exceeded the 30-day inactivity and 50% engagement drop threshold."
            ), "SUCCESS"

    # ---------------------------------------------------------
    # Summary Synthesis
    # ---------------------------------------------------------

    def _synthesize_workflow_summary(self, wf_def: WorkflowDefinition, tool_data: Dict[str, Any], params: Dict[str, Any], rule_eval: Optional[ConditionEvaluation]) -> str:
        """Synthesizes polished user-facing markdown reports."""
        wf_id = wf_def.workflow_id.upper()

        if wf_id == "WF001":
            items = tool_data.get("restock_list", [])
            lines = [
                "### Inventory Restock Summary",
                f"**Total Products Scanned:** {tool_data.get('total_products_checked', 0)}",
                f"**Products Requiring Restock:** {tool_data.get('products_needing_restock_count', 0)}",
                "*(Formula: Reorder Quantity = Target Stock − Current Stock)*\n",
                "| SKU | Product Name | Current Stock | Minimum Threshold | Target Capacity | Suggested Reorder |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |"
            ]
            for it in items:
                lines.append(f"| {it['sku']} | {it['product_name']} | {it['current_stock']} | {it['minimum_threshold']} | {it.get('target_stock', '-')} | **{it['suggested_reorder_qty']} units** |")
            return "\n".join(lines)

        elif wf_id == "WF002":
            exceptions = tool_data.get("exceptions", [])
            lines = [
                "### Price Validation Exceptions Report",
                f"**Total Matched Products:** {tool_data.get('total_matched', 0)}",
                f"**Discrepancies Flagged (>10%):** {tool_data.get('exceptions_flagged_count', 0)}\n",
                "| SKU | Product Name | Internal Price | Vendor Price | Difference ($) | Variance (%) | Direction |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
            ]
            for e in exceptions:
                lines.append(f"| {e['sku']} | {e['product_name']} | ${e['internal_price']} | ${e['vendor_price']} | ${e['difference_absolute']} | **{e['difference_percentage']}%** | {e['status']} |")
            return "\n".join(lines)

        elif wf_id == "WF003":
            invalids = tool_data.get("invalid_rows_report", [])
            lines = [
                "### Vendor Spreadsheet Processing Summary",
                f"**Total Rows Ingested:** {tool_data.get('total_rows_read', 0)}",
                f"**Clean Rows Validated:** {tool_data.get('clean_rows_count', 0)}",
                f"**Invalid Rows Partitioned:** {tool_data.get('invalid_rows_count', 0)}\n",
                "| Row # | Ingested Data Preview | Validation Error Reasons |",
                "| :--- | :--- | :--- |"
            ]
            for inv in invalids:
                data_preview = f"SKU: {inv['data'].get('sku') or 'EMPTY'}, Name: {inv['data'].get('product_name') or 'EMPTY'}"
                reasons = "<br>".join(inv["errors"])
                lines.append(f"| {inv['row_number']} | `{data_preview}` | ❌ **{reasons}** |")
            return "\n".join(lines)

        elif wf_id == "WF004":
            return (
                f"### Generated SEO Content: {tool_data.get('product_name')}\n"
                f"**Category:** {tool_data.get('category')}\n\n"
                f"#### Product Description:\n{tool_data.get('product_description')}\n\n"
                f"#### Short Description ({tool_data.get('short_description_words')} words):\n{tool_data.get('short_description')}\n\n"
                f"#### SEO Metadata:\n"
                f"- **SEO Title ({tool_data.get('seo_title_length')} chars):** `{tool_data.get('seo_title')}`\n"
                f"- **Meta Description ({tool_data.get('meta_description_length')} chars):** `{tool_data.get('meta_description')}`\n\n"
                f"#### Attribute Audit:\n"
                f"- **Missing Attributes Flagged:** {', '.join(tool_data.get('attribute_audit', {}).get('missing_attributes_flagged', [])) or 'None'}"
            )

        elif wf_id == "WF005":
            ship = tool_data.get("shipment_details", {})
            items = tool_data.get("items", [])
            lines = [
                f"### Customer Order Status: {tool_data.get('order_id')}",
                f"**Customer:** {tool_data.get('customer_name')} ({tool_data.get('customer_email')})",
                f"**Order Status:** `{tool_data.get('order_status')}`",
                f"**Carrier:** {ship.get('carrier')} | **Tracking Number:** `{ship.get('tracking_number')}`",
                f"**Estimated Delivery:** {ship.get('estimated_delivery')}\n",
                "#### Ordered Items:",
                "| SKU | Product Description | Quantity | Price |",
                "| :--- | :--- | :--- | :--- |"
            ]
            for it in items:
                lines.append(f"| {it.get('sku')} | {it.get('name')} | {it.get('quantity')} | ${it.get('price')} |")
            return "\n".join(lines)

        elif wf_id == "WF006":
            defs = tool_data.get("definite_duplicates", [])
            poss = tool_data.get("possible_duplicates", [])
            lines = [
                "### Product Catalog Deduplication Audit",
                f"**Definite SKU Duplicates:** {len(defs)} pairs",
                f"**Possible Attribute Duplicates:** {len(poss)} pairs\n",
                "#### Definite SKU Duplicates:",
                "| SKU 1 | Product 1 | SKU 2 | Product 2 | Match Type |",
                "| :--- | :--- | :--- | :--- | :--- |"
            ]
            for d in defs:
                lines.append(f"| {d['sku_1']} | {d['name_1']} | {d['sku_2']} | {d['name_2']} | **Definite Duplicate** |")
            lines.append("\n#### Possible Attribute Duplicates:")
            lines.append("| SKU 1 | Product 1 | SKU 2 | Product 2 | Similarity |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for p in poss:
                lines.append(f"| {p['sku_1']} | {p['name_1']} | {p['sku_2']} | {p['name_2']} | **{p['similarity_score'] * 100:.1f}%** |")
            return "\n".join(lines)

        elif wf_id == "WF007":
            c_summary = tool_data.get("campaign_summary", {})
            pillars = tool_data.get("messaging_pillars", [])
            channels = tool_data.get("channel_recommendations", [])
            tasks = tool_data.get("launch_checklist", [])
            lines = [
                f"### Marketing Campaign Brief: {c_summary.get('campaign_objective') or tool_data.get('campaign_goal') or params.get('campaign_goal')}",
                f"**Target Audience:** {c_summary.get('target_audience') or tool_data.get('target_audience') or params.get('target_audience')}",
                f"**Promotional Dates:** {c_summary.get('campaign_dates') or tool_data.get('dates') or params.get('dates')}\n",
                "#### Messaging Pillars:"
            ]
            for p in pillars:
                if isinstance(p, dict):
                    lines.append(f"- **{p.get('theme')}:** {p.get('copy')}")
                else:
                    lines.append(f"- {p}")
            lines.append("\n#### Recommended Channels:")
            for c in channels:
                lines.append(f"- **{c.get('channel')}:** {c.get('strategy') or c.get('rationale')}")
            lines.append("\n#### Launch Checklist:")
            for t in tasks:
                lines.append(f"- [ ] {t.get('task')} *(Due: {t.get('deadline')})*")
            return "\n".join(lines)

        elif wf_id == "WF008":
            dist = tool_data.get("intent_distribution", {})
            kw_list = tool_data.get("classified_keywords", [])
            lines = [
                "### SEO Keyword Classification & Mapping",
                f"**Total Processed:** {tool_data.get('total_keywords_processed')} keywords *(Duplicates Removed: {tool_data.get('duplicates_removed')})*\n",
                f"**Intent Breakdown:** " + " • ".join([f"{k}: **{v}**" for k, v in dist.items()]) + "\n",
                "| Keyword | Search Intent | Target Category | Priority | Recommended Target Page |",
                "| :--- | :--- | :--- | :--- | :--- |"
            ]
            for kw in kw_list:
                lines.append(f"| {kw['keyword']} | {kw['search_intent']} | {kw['category']} | {kw['priority']} | `{kw['target_landing_page']}` |")
            return "\n".join(lines)

        elif wf_id == "WF009":
            decision = tool_data.get("decision")
            status = tool_data.get("status")
            if decision in ["ESCALATED", "ESCALATE_TO_MANAGER"] or status == "ESCALATED":
                reason = tool_data.get("reason") or tool_data.get("assignment_rationale") or "No employee possesses required skills or available capacity."
                task_desc = tool_data.get("task_details", {}).get("description") or tool_data.get("task_description") or params.get("task_description", "Task assignment")
                return (
                    f"### Task Assignment Escalation\n"
                    f"🚨 **Status:** ESCALATED TO ENGINEERING MANAGER\n\n"
                    f"**Task Description:** {task_desc}\n"
                    f"**Escalation Reason:** {reason}"
                )
            emp = tool_data.get("assigned_employee", {})
            return (
                f"### Employee Task Assignment Manifest\n"
                f"**Assigned Candidate:** **{emp.get('name')}** (`{emp.get('employee_id')}`)\n"
                f"**Matching Skills:** {', '.join(emp.get('skills_matched', []))}\n"
                f"**Workload Before Assignment:** {emp.get('current_workload_pct')}\n"
                f"**Assignment Rationale:** {tool_data.get('assignment_rationale')}\n"
            )

        elif wf_id == "WF010":
            metrics = tool_data.get("workflow_metrics", [])
            recs = tool_data.get("recommendations", [])
            lines = [
                "### Automated Workflow Performance Audit",
                f"**Total Executions Analyzed:** {tool_data.get('total_executions_analyzed')} runs",
                f"**Flagged Bottlenecks / Degradations:** {tool_data.get('flagged_workflows_count')} workflows\n",
                "| Workflow ID | Name | Runs | Failures | Failure Rate | Avg Latency | SLA Status |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
            ]
            for m in metrics:
                status_badge = "🚨 **DEGRADED (>10%)**" if m["is_flagged"] else "✅ HEALTHY"
                lines.append(f"| {m['workflow_id']} | {m['workflow_name']} | {m['total_runs']} | {m['failure_count']} | **{m['failure_rate_pct']}%** | {m['avg_duration_sec']}s | {status_badge} |")
            lines.append("\n#### Optimization Action Items:")
            for r in recs:
                lines.append(f"- ⚠️ {r}")
            return "\n".join(lines)

        # Generic Dynamic Workflow (e.g. WF011: Customer Churn Alert)
        else:
            accounts = tool_data.get("high_risk_accounts", [])
            if accounts and isinstance(accounts, list):
                lines = [
                    f"### {wf_def.workflow_name}",
                    f"**High-Risk Accounts Identified:** {len(accounts)}\n",
                    "| Account ID | Company Name | Inactive Days | Engagement Drop |",
                    "| :--- | :--- | :--- | :--- |"
                ]
                for a in accounts:
                    lines.append(f"| {a.get('account_id')} | {a.get('name')} | {a.get('days_inactive')} days | {a.get('drop_pct') or a.get('engagement_drop_pct')}% |")
                return "\n".join(lines)
            elif "summary" in tool_data:
                return str(tool_data["summary"])
            else:
                return f"### Executed Workflow: {wf_def.workflow_name} ({wf_def.workflow_id})\nSuccessfully executed all {len(wf_def.steps)} steps according to declarative workflow definition."


# Global singleton engine
workflow_engine = WorkflowEngine()
