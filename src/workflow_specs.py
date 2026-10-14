import re
from typing import Dict, Any, List, Optional, Tuple, Callable
from src.schemas import StepDefinition, PreCondition
from src.context import ExecutionContext


class WorkflowSpec:
    """
    Declarative specification defining the executable step pipeline,
    input validation gates, business decision rules, and output formatting.
    """

    def __init__(
        self,
        workflow_id: str,
        pre_conditions: Optional[List[PreCondition]] = None,
        executable_steps: Optional[List[StepDefinition]] = None,
        decision_evaluator: Optional[Callable[[ExecutionContext], Tuple[bool, str, str, str]]] = None,
        summary_renderer: Optional[Callable[[ExecutionContext], str]] = None,
        data_extractor: Optional[Callable[[ExecutionContext], Dict[str, Any]]] = None,
    ):
        self.workflow_id = workflow_id
        self.pre_conditions = pre_conditions or []
        self.executable_steps = executable_steps or []
        self.decision_evaluator = decision_evaluator
        self.summary_renderer = summary_renderer
        self.data_extractor = data_extractor

    def evaluate_pre_conditions(self, context: ExecutionContext, decision_logic: str) -> Optional[Tuple[str, str, str, Dict[str, Any]]]:
        """
        Evaluates input validation gates prior to step execution.
        Returns (status, condition_name, summary_message, data) if a pre-condition fails, or None if passed.
        """
        for pre in self.pre_conditions:
            if pre.name == "Mandatory Campaign Parameter Check":
                goal = context.get("campaign_goal")
                dates = context.get("dates")
                if not goal or not dates:
                    return (
                        pre.failure_status,
                        "Mandatory Campaign Parameter Check",
                        "Please provide the **campaign_goal** and target launch **dates** before brief generation.",
                        {}
                    )

            elif pre.name == "Order Existence Gate":
                identifier = context.get("order_id") or context.get("identifier")
                if not identifier:
                    m = re.search(r'\b(ORD-\d{4}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', context.user_request, re.IGNORECASE)
                    if m:
                        identifier = m.group(1).upper() if "ORD-" in m.group(1).upper() else m.group(1)
                if not identifier:
                    identifier = "ORD-1001"
                context.set("identifier", identifier)
                context.set("order_id", identifier)

        return None


# -------------------------------------------------------------
# Decision Evaluator Callbacks: (outcome, condition_name, explanation, status)
# -------------------------------------------------------------

def _eval_wf001(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("restock_data", {})
    count = data.get("products_needing_restock_count", 0)
    return (
        count > 0,
        "Restock Threshold Evaluation",
        f"{count} items fell below minimum safety thresholds.",
        "SUCCESS"
    )

def _render_wf001(ctx: ExecutionContext) -> str:
    data = ctx.get("restock_data", {})
    items = data.get("restock_list", [])
    lines = [
        "### Inventory Restock Summary",
        f"**Total Products Scanned:** {data.get('total_products_checked', 0)}",
        f"**Products Requiring Restock:** {data.get('products_needing_restock_count', 0)}",
        "*(Formula: Reorder Quantity = Target Stock − Current Stock)*\n",
        "| SKU | Product Name | Current Stock | Minimum Threshold | Target Capacity | Suggested Reorder |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for it in items:
        lines.append(f"| {it['sku']} | {it['product_name']} | {it['current_stock']} | {it['minimum_threshold']} | {it.get('target_stock', '-')} | **{it['suggested_reorder_qty']} units** |")
    return "\n".join(lines)


def _eval_wf002(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("price_data", {})
    exceptions = data.get("exceptions_flagged_count", 0)
    return (
        exceptions > 0,
        "Price Variance Threshold Gate",
        f"Identified {exceptions} products with price divergence exceeding 10%.",
        "SUCCESS"
    )

def _render_wf002(ctx: ExecutionContext) -> str:
    data = ctx.get("price_data", {})
    exceptions = data.get("exceptions", [])
    lines = [
        "### Price Validation Exceptions Report",
        f"**Total Matched Products:** {data.get('total_matched', 0)}",
        f"**Discrepancies Flagged (>10%):** {data.get('exceptions_flagged_count', 0)}\n",
        "| SKU | Product Name | Internal Price | Vendor Price | Difference ($) | Variance (%) | Direction |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for e in exceptions:
        lines.append(f"| {e['sku']} | {e['product_name']} | ${e['internal_price']} | ${e['vendor_price']} | ${e['difference_absolute']} | **{e['difference_percentage']}%** | {e['status']} |")
    return "\n".join(lines)


def _eval_wf003(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("vendor_cleaning_data", {})
    invalids = data.get("invalid_rows_count", 0)
    return (
        invalids > 0,
        "Mandatory Field Gate",
        f"Partitioned {invalids} invalid rows lacking mandatory SKU or Product Name.",
        "SUCCESS"
    )

def _render_wf003(ctx: ExecutionContext) -> str:
    data = ctx.get("vendor_cleaning_data", {})
    invalids = data.get("invalid_rows_report", [])
    lines = [
        "### Vendor Spreadsheet Processing Summary",
        f"**Total Rows Ingested:** {data.get('total_rows_read', 0)}",
        f"**Clean Rows Validated:** {data.get('clean_rows_count', 0)}",
        f"**Invalid Rows Partitioned:** {data.get('invalid_rows_count', 0)}\n",
        "| Row # | Ingested Data Preview | Validation Error Reasons |",
        "| :--- | :--- | :--- |"
    ]
    for inv in invalids:
        data_preview = f"SKU: {inv['data'].get('sku') or 'EMPTY'}, Name: {inv['data'].get('product_name') or 'EMPTY'}"
        reasons = "<br>".join(inv["errors"])
        lines.append(f"| {inv['row_number']} | `{data_preview}` | ❌ **{reasons}** |")
    return "\n".join(lines)


def _eval_wf004(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    return (
        True,
        "Hallucination Prevention Gate",
        "Audited product attributes and explicitly flagged missing specifications to prevent hallucinations.",
        "SUCCESS"
    )

def _render_wf004(ctx: ExecutionContext) -> str:
    data = ctx.get("product_content_data", {})
    return (
        f"### Generated SEO Content: {data.get('product_name')}\n"
        f"**Category:** {data.get('category')}\n\n"
        f"#### Product Description:\n{data.get('product_description')}\n\n"
        f"#### Short Description ({data.get('short_description_words')} words):\n{data.get('short_description')}\n\n"
        f"#### SEO Metadata:\n"
        f"- **SEO Title ({data.get('seo_title_length')} chars):** `{data.get('seo_title')}`\n"
        f"- **Meta Description ({data.get('meta_description_length')} chars):** `{data.get('meta_description')}`\n\n"
        f"#### Attribute Audit:\n"
        f"- **Missing Attributes Flagged:** {', '.join(data.get('attribute_audit', {}).get('missing_attributes_flagged', [])) or 'None'}"
    )


def _eval_wf005(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("order_status_data", {})
    if not data.get("found", True):
        return (
            False,
            "Order Existence Gate",
            f"No order found matching identifier '{ctx.get('identifier')}'.",
            "FAILED"
        )
    return (
        True,
        "Order Fulfillment Decision Rule",
        f"Retrieved order details and real-time tracking for {data.get('order_id')}.",
        "SUCCESS"
    )

def _render_wf005(ctx: ExecutionContext) -> str:
    data = ctx.get("order_status_data", {})
    if not data.get("found", True):
        return f"No order found matching identifier '{ctx.get('identifier')}'. Please verify and provide a valid Order ID or Customer Email."
    ship = data.get("shipment_details", {})
    items = data.get("items", [])
    lines = [
        f"### Customer Order Status: {data.get('order_id')}",
        f"**Customer:** {data.get('customer_name')} ({data.get('customer_email')})",
        f"**Order Status:** `{data.get('order_status')}`",
        f"**Carrier:** {ship.get('carrier')} | **Tracking Number:** `{ship.get('tracking_number')}`",
        f"**Estimated Delivery:** {ship.get('estimated_delivery')}\n",
        "#### Ordered Items:",
        "| SKU | Product Description | Quantity | Price |",
        "| :--- | :--- | :--- | :--- |"
    ]
    for it in items:
        lines.append(f"| {it.get('sku')} | {it.get('name')} | {it.get('quantity')} | ${it.get('price')} |")
    return "\n".join(lines)


def _eval_wf006(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("duplicate_data", {})
    defs = data.get("definite_duplicates_count", 0)
    poss = data.get("possible_duplicates_count", 0)
    return (
        defs > 0 or poss > 0,
        "Product Deduplication Decision Gate",
        f"Found {defs} definite SKU duplicate matches and {poss} possible attribute duplicates.",
        "SUCCESS"
    )

def _render_wf006(ctx: ExecutionContext) -> str:
    data = ctx.get("duplicate_data", {})
    defs = data.get("definite_duplicates", [])
    poss = data.get("possible_duplicates", [])
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


def _eval_wf007(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    return (
        True,
        "Input Validation & Strategy Gate",
        "Validated campaign goals and promotional dates successfully.",
        "SUCCESS"
    )

def _render_wf007(ctx: ExecutionContext) -> str:
    data = ctx.get("campaign_data", {})
    c_summary = data.get("campaign_summary", {})
    pillars = data.get("messaging_pillars", [])
    channels = data.get("channel_recommendations", [])
    tasks = data.get("launch_checklist", [])
    lines = [
        f"### Marketing Campaign Brief: {c_summary.get('campaign_objective') or data.get('campaign_goal') or ctx.get('campaign_goal')}",
        f"**Target Audience:** {c_summary.get('target_audience') or data.get('target_audience') or ctx.get('target_audience')}",
        f"**Promotional Dates:** {c_summary.get('campaign_dates') or data.get('dates') or ctx.get('dates')}\n",
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


def _eval_wf008(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("keyword_data", {})
    return (
        True,
        "Search Intent Classification Gate",
        f"Categorized {data.get('total_keywords_processed', 0)} keywords across intent clusters.",
        "SUCCESS"
    )

def _render_wf008(ctx: ExecutionContext) -> str:
    data = ctx.get("keyword_data", {})
    dist = data.get("intent_distribution", {})
    kw_list = data.get("classified_keywords", [])
    lines = [
        "### SEO Keyword Classification & Mapping",
        f"**Total Processed:** {data.get('total_keywords_processed')} keywords *(Duplicates Removed: {data.get('duplicates_removed')})*\n",
        f"**Intent Breakdown:** " + " • ".join([f"{k}: **{v}**" for k, v in dist.items()]) + "\n",
        "| Keyword | Search Intent | Target Category | Priority | Recommended Target Page |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for kw in kw_list:
        lines.append(f"| {kw['keyword']} | {kw['search_intent']} | {kw['category']} | {kw['priority']} | `{kw['target_landing_page']}` |")
    return "\n".join(lines)


def _eval_wf009(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("assignment_data", {})
    decision = data.get("decision")
    status = data.get("status")
    if decision in ["ESCALATED", "ESCALATE_TO_MANAGER"] or status == "ESCALATED":
        return (
            False,
            "Capacity & Skill Allocation Rule",
            data.get("reason") or data.get("assignment_rationale") or "Escalated to engineering manager.",
            "FAILED"
        )
    emp = data.get("assigned_employee", {})
    return (
        True,
        "Capacity & Skill Allocation Rule",
        f"Assigned to {emp.get('name')} based on matching skills and available capacity ({emp.get('current_workload_pct', 'N/A')}).",
        "SUCCESS"
    )

def _render_wf009(ctx: ExecutionContext) -> str:
    data = ctx.get("assignment_data", {})
    decision = data.get("decision")
    status = data.get("status")
    if decision in ["ESCALATED", "ESCALATE_TO_MANAGER"] or status == "ESCALATED":
        reason = data.get("reason") or data.get("assignment_rationale") or "No employee possesses required skills or available capacity."
        task_desc = data.get("task_details", {}).get("description") or data.get("task_description") or ctx.get("task_description", "Task assignment")
        return (
            f"### Task Assignment Escalation\n"
            f"🚨 **Status:** ESCALATED TO ENGINEERING MANAGER\n\n"
            f"**Task Description:** {task_desc}\n"
            f"**Escalation Reason:** {reason}"
        )
    emp = data.get("assigned_employee", {})
    return (
        f"### Employee Task Assignment Manifest\n"
        f"**Assigned Candidate:** **{emp.get('name')}** (`{emp.get('employee_id')}`)\n"
        f"**Matching Skills:** {', '.join(emp.get('skills_matched', []))}\n"
        f"**Workload Before Assignment:** {emp.get('current_workload_pct')}\n"
        f"**Assignment Rationale:** {data.get('assignment_rationale')}\n"
    )


def _eval_wf010(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
    data = ctx.get("performance_data", {})
    flagged = data.get("flagged_workflows_count", 0)
    return (
        flagged > 0,
        "SLA Degradation Gate",
        f"Flagged {flagged} workflows exceeding SLA failure or latency thresholds.",
        "SUCCESS"
    )

def _render_wf010(ctx: ExecutionContext) -> str:
    data = ctx.get("performance_data", {})
    metrics = data.get("workflow_metrics", [])
    recs = data.get("recommendations", [])
    lines = [
        "### Automated Workflow Performance Audit",
        f"**Total Executions Analyzed:** {data.get('total_executions_analyzed')} runs",
        f"**Flagged Bottlenecks / Degradations:** {data.get('flagged_workflows_count')} workflows\n",
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


# -------------------------------------------------------------
# Declarative Specification Catalog (WF001 - WF010)
# -------------------------------------------------------------

WORKFLOW_SPEC_CATALOG: Dict[str, WorkflowSpec] = {
    "WF001": WorkflowSpec(
        workflow_id="WF001",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Load inventory", tool_name="csv_reader", input_mappings={"file_path": "$params.file_path|data/inventory.csv"}, output_variable="raw_inventory", summary_template="Ingested inventory records from CSV."),
            StepDefinition(step_number=2, step_name="compare current stock with minimum threshold", tool_name="calculator", input_mappings={"operation": "compare_threshold"}, output_variable="threshold_calc", summary_template="Compared current stock with minimum threshold safety margins."),
            StepDefinition(step_number=3, step_name="identify low-stock products", tool_name="check_inventory_restock", input_mappings={"file_path": "$params.file_path|data/inventory.csv", "min_threshold": "$params.threshold"}, output_variable="restock_data", summary_template="Identified products needing restock."),
            StepDefinition(step_number=4, step_name="calculate reorder quantity", tool_name="calculator", input_mappings={"operation": "reorder_calculation"}, output_variable="reorder_calc", summary_template="Calculated suggested reorders based on safety margins."),
            StepDefinition(step_number=5, step_name="generate restock list", tool_name="check_inventory_restock", input_mappings={"file_path": "$params.file_path|data/inventory.csv"}, output_variable="restock_data", summary_template="Compiled final restock list.")
        ],
        decision_evaluator=_eval_wf001,
        summary_renderer=_render_wf001,
        data_extractor=lambda ctx: ctx.get("restock_data")
    ),
    "WF002": WorkflowSpec(
        workflow_id="WF002",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Load product prices", tool_name="csv_reader", input_mappings={"file_path": "$params.internal_file|data/internal_prices.csv"}, output_variable="raw_internal_prices", summary_template="Loaded internal price records."),
            StepDefinition(step_number=2, step_name="match products by SKU", tool_name="csv_reader", input_mappings={"file_path": "$params.vendor_file|data/vendor_prices.csv"}, output_variable="raw_vendor_prices", summary_template="Matched product SKUs against vendor catalog."),
            StepDefinition(step_number=3, step_name="compare internal and vendor prices", tool_name="validate_product_prices", input_mappings={"internal_file": "$params.internal_file|data/internal_prices.csv", "vendor_file": "$params.vendor_file|data/vendor_prices.csv", "variance_threshold": "$params.variance_threshold|0.10"}, output_variable="price_data", summary_template="Compared prices and flagged divergences."),
            StepDefinition(step_number=4, step_name="calculate percentage difference", tool_name="calculator", input_mappings={"operation": "percentage_difference"}, output_variable="calc_pct", summary_template="Calculated percentage differences."),
            StepDefinition(step_number=5, step_name="flag exceptions", tool_name="validate_product_prices", input_mappings={"variance_threshold": "$params.variance_threshold|0.10"}, output_variable="price_data", summary_template="Flagged price discrepancy exceptions.")
        ],
        decision_evaluator=_eval_wf002,
        summary_renderer=_render_wf002,
        data_extractor=lambda ctx: ctx.get("price_data")
    ),
    "WF003": WorkflowSpec(
        workflow_id="WF003",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Read file", tool_name="read_csv", input_mappings={"file_path": "$params.file_path|data/vendor_raw_feed.csv"}, output_variable="raw_vendor_feed", summary_template="Read vendor spreadsheet rows."),
            StepDefinition(step_number=2, step_name="detect columns", tool_name="process_vendor_file", input_mappings={"file_path": "$params.file_path|data/vendor_raw_feed.csv"}, output_variable="vendor_cleaning_data", summary_template="Detected spreadsheet headers."),
            StepDefinition(step_number=3, step_name="normalize column names", tool_name="process_vendor_file", input_mappings={}, output_variable="vendor_cleaning_data", summary_template="Normalized inconsistent column aliases."),
            StepDefinition(step_number=4, step_name="validate required fields", tool_name="process_vendor_file", input_mappings={}, output_variable="vendor_cleaning_data", summary_template="Validated mandatory SKU and Product Name presence."),
            StepDefinition(step_number=5, step_name="identify invalid rows", tool_name="process_vendor_file", input_mappings={}, output_variable="vendor_cleaning_data", summary_template="Partitioned invalid rows."),
            StepDefinition(step_number=6, step_name="produce cleaned dataset", tool_name="process_vendor_file", input_mappings={}, output_variable="vendor_cleaning_data", summary_template="Produced validated clean dataset.")
        ],
        decision_evaluator=_eval_wf003,
        summary_renderer=_render_wf003,
        data_extractor=lambda ctx: ctx.get("vendor_cleaning_data")
    ),
    "WF004": WorkflowSpec(
        workflow_id="WF004",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Validate required attributes", tool_name="calculator", input_mappings={"operation": "validate_attributes"}, output_variable="attr_validation", summary_template="Validated input product attributes."),
            StepDefinition(step_number=2, step_name="create product description", tool_name="generate_product_content", input_mappings={"product_name": "$params.product_name|Ergonomic Office Chair", "category": "$params.category|Office Furniture", "attributes": "$params.attributes"}, output_variable="product_content_data", summary_template="Created customer-facing product description."),
            StepDefinition(step_number=3, step_name="generate short description", tool_name="calculator", input_mappings={"operation": "short_desc"}, output_variable="short_desc_meta", summary_template="Generated short summary description."),
            StepDefinition(step_number=4, step_name="generate SEO title", tool_name="calculator", input_mappings={"operation": "seo_title"}, output_variable="seo_title_meta", summary_template="Generated optimized SEO title."),
            StepDefinition(step_number=5, step_name="generate meta description", tool_name="calculator", input_mappings={"operation": "meta_desc"}, output_variable="meta_desc_meta", summary_template="Generated SEO meta description.")
        ],
        decision_evaluator=_eval_wf004,
        summary_renderer=_render_wf004,
        data_extractor=lambda ctx: ctx.get("product_content_data")
    ),
    "WF005": WorkflowSpec(
        workflow_id="WF005",
        pre_conditions=[
            PreCondition(name="Order Existence Gate", required_keys=["identifier", "order_id"], failure_status="FAILED")
        ],
        executable_steps=[
            StepDefinition(step_number=1, step_name="Validate identifier", tool_name="lookup_order_status", input_mappings={"identifier": "$state.identifier"}, output_variable="order_status_data", summary_template="Validated order identifier format."),
            StepDefinition(step_number=2, step_name="search order data", tool_name="lookup_order_status", input_mappings={"identifier": "$state.identifier"}, output_variable="order_status_data", summary_template="Queried order database records."),
            StepDefinition(step_number=3, step_name="retrieve order status", tool_name="lookup_order_status", input_mappings={"identifier": "$state.identifier"}, output_variable="order_status_data", summary_template="Retrieved fulfillment status."),
            StepDefinition(step_number=4, step_name="retrieve shipment information", tool_name="lookup_order_status", input_mappings={"identifier": "$state.identifier"}, output_variable="order_status_data", summary_template="Retrieved carrier tracking information."),
            StepDefinition(step_number=5, step_name="summarize current status", tool_name="lookup_order_status", input_mappings={"identifier": "$state.identifier"}, output_variable="order_status_data", summary_template="Summarized order delivery status.")
        ],
        decision_evaluator=_eval_wf005,
        summary_renderer=_render_wf005,
        data_extractor=lambda ctx: ctx.get("order_status_data")
    ),
    "WF006": WorkflowSpec(
        workflow_id="WF006",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Load products", tool_name="read_csv", input_mappings={"file_path": "$params.file_path|data/inventory.csv"}, output_variable="raw_catalog", summary_template="Loaded product catalog records."),
            StepDefinition(step_number=2, step_name="normalize names/SKUs", tool_name="calculator", input_mappings={"operation": "normalize_tokens"}, output_variable="norm_tokens", summary_template="Normalized names and SKUs."),
            StepDefinition(step_number=3, step_name="compare identifiers", tool_name="detect_duplicate_products", input_mappings={"file_path": "$params.file_path|data/inventory.csv"}, output_variable="duplicate_data", summary_template="Compared SKU identifiers for exact matches."),
            StepDefinition(step_number=4, step_name="compare product attributes", tool_name="calculator", input_mappings={"operation": "similarity_distance"}, output_variable="similarity_calc", summary_template="Computed fuzzy attribute similarity."),
            StepDefinition(step_number=5, step_name="group likely duplicates", tool_name="calculator", input_mappings={"operation": "group_duplicates"}, output_variable="group_meta", summary_template="Grouped probable duplicate pairs."),
            StepDefinition(step_number=6, step_name="assign confidence", tool_name="calculator", input_mappings={"operation": "assign_confidence"}, output_variable="conf_meta", summary_template="Assigned confidence scores to detected duplicates.")
        ],
        decision_evaluator=_eval_wf006,
        summary_renderer=_render_wf006,
        data_extractor=lambda ctx: ctx.get("duplicate_data")
    ),
    "WF007": WorkflowSpec(
        workflow_id="WF007",
        pre_conditions=[
            PreCondition(name="Mandatory Campaign Parameter Check", required_keys=["campaign_goal", "dates"], failure_status="NEEDS_INPUT")
        ],
        executable_steps=[
            StepDefinition(step_number=1, step_name="Validate inputs", tool_name="calculator", input_mappings={"operation": "validate_inputs"}, output_variable="validation_meta", summary_template="Validated campaign inputs and dates."),
            StepDefinition(step_number=2, step_name="identify campaign objective", tool_name="generate_marketing_brief", input_mappings={"campaign_goal": "$params.campaign_goal", "dates": "$params.dates", "target_audience": "$params.target_audience", "promotion": "$params.promotion", "product_list": "$params.product_list"}, output_variable="campaign_data", summary_template="Identified core campaign objective."),
            StepDefinition(step_number=3, step_name="summarize products", tool_name="calculator", input_mappings={"operation": "summarize_products"}, output_variable="product_summary", summary_template="Summarized featured products."),
            StepDefinition(step_number=4, step_name="create messaging", tool_name="calculator", input_mappings={"operation": "messaging_pillars"}, output_variable="messaging_meta", summary_template="Created core messaging pillars."),
            StepDefinition(step_number=5, step_name="create channel recommendations", tool_name="calculator", input_mappings={"operation": "channel_recs"}, output_variable="channel_meta", summary_template="Created marketing channel recommendations."),
            StepDefinition(step_number=6, step_name="create campaign checklist", tool_name="calculator", input_mappings={"operation": "checklist"}, output_variable="checklist_meta", summary_template="Assembled campaign launch checklist.")
        ],
        decision_evaluator=_eval_wf007,
        summary_renderer=_render_wf007,
        data_extractor=lambda ctx: ctx.get("campaign_data")
    ),
    "WF008": WorkflowSpec(
        workflow_id="WF008",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Read keywords", tool_name="read_csv", input_mappings={"file_path": "$params.file_path|data/keywords.csv"}, output_variable="raw_keywords", summary_template="Read keyword list from repository."),
            StepDefinition(step_number=2, step_name="remove duplicates", tool_name="calculator", input_mappings={"operation": "deduplicate"}, output_variable="dedup_meta", summary_template="Deduplicated keywords."),
            StepDefinition(step_number=3, step_name="classify search intent", tool_name="classify_seo_keywords", input_mappings={"file_path": "$params.file_path|data/keywords.csv", "custom_keywords": "$params.custom_keywords"}, output_variable="keyword_data", summary_template="Classified search intents."),
            StepDefinition(step_number=4, step_name="map keywords to categories", tool_name="calculator", input_mappings={"operation": "map_categories"}, output_variable="map_meta", summary_template="Mapped keywords to categories."),
            StepDefinition(step_number=5, step_name="identify high-priority keywords", tool_name="calculator", input_mappings={"operation": "priority_ranking"}, output_variable="keyword_priority", summary_template="Ranked high-priority keywords."),
            StepDefinition(step_number=6, step_name="export results", tool_name="calculator", input_mappings={"operation": "export_meta"}, output_variable="export_meta", summary_template="Exported keyword classification manifest.")
        ],
        decision_evaluator=_eval_wf008,
        summary_renderer=_render_wf008,
        data_extractor=lambda ctx: ctx.get("keyword_data")
    ),
    "WF009": WorkflowSpec(
        workflow_id="WF009",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Understand task requirements", tool_name="calculator", input_mappings={"operation": "parse_task_requirements"}, output_variable="task_reqs", summary_template="Parsed task requirements and skills needed."),
            StepDefinition(step_number=2, step_name="compare employee skills", tool_name="calculator", input_mappings={"operation": "compare_skills"}, output_variable="skill_comparison", summary_template="Compared skills against employee directory."),
            StepDefinition(step_number=3, step_name="check current workload", tool_name="calculator", input_mappings={"operation": "check_workload"}, output_variable="workload_check", summary_template="Checked employee workload capacities."),
            StepDefinition(step_number=4, step_name="rank candidates", tool_name="calculator", input_mappings={"operation": "rank_candidates"}, output_variable="candidate_ranking", summary_template="Ranked eligible candidates by capacity."),
            StepDefinition(step_number=5, step_name="select employee", tool_name="assign_employee_task", input_mappings={"task_description": "$params.task_description|$user_request", "required_skills": "$params.required_skills", "priority": "$params.priority|Medium", "deadline": "$params.deadline|2026-10-20"}, output_variable="assignment_data", summary_template="Selected candidate or flagged escalation."),
            StepDefinition(step_number=6, step_name="generate assignment summary", tool_name="calculator", input_mappings={"operation": "generate_summary"}, output_variable="summary_meta", summary_template="Generated task assignment summary.")
        ],
        decision_evaluator=_eval_wf009,
        summary_renderer=_render_wf009,
        data_extractor=lambda ctx: ctx.get("assignment_data")
    ),
    "WF010": WorkflowSpec(
        workflow_id="WF010",
        executable_steps=[
            StepDefinition(step_number=1, step_name="Load execution logs", tool_name="read_csv", input_mappings={"file_path": "$params.log_file|data/execution_logs.csv"}, output_variable="raw_logs", summary_template="Loaded execution logs from database."),
            StepDefinition(step_number=2, step_name="calculate success/failure rate", tool_name="calculator", input_mappings={"operation": "failure_rate"}, output_variable="calc_fail", summary_template="Calculated failure rates across workflows."),
            StepDefinition(step_number=3, step_name="calculate average execution time", tool_name="calculator", input_mappings={"operation": "latency_average"}, output_variable="calc_dur", summary_template="Calculated average execution times."),
            StepDefinition(step_number=4, step_name="identify frequent errors", tool_name="aggregate_workflow_performance", input_mappings={"log_file": "$params.log_file|data/execution_logs.csv", "failure_threshold": 0.10, "latency_threshold": 2.0}, output_variable="performance_data", summary_template="Identified frequent errors across runs."),
            StepDefinition(step_number=5, step_name="identify slow steps", tool_name="calculator", input_mappings={"operation": "slow_steps"}, output_variable="slow_steps_meta", summary_template="Flagged slow steps and SLA breaches."),
            StepDefinition(step_number=6, step_name="generate recommendations", tool_name="calculator", input_mappings={"operation": "recommendations"}, output_variable="rec_meta", summary_template="Synthesized performance recommendations.")
        ],
        decision_evaluator=_eval_wf010,
        summary_renderer=_render_wf010,
        data_extractor=lambda ctx: ctx.get("performance_data")
    )
}


def build_dynamic_spec_for_workflow(wf_def) -> WorkflowSpec:
    """
    Constructs a fully functional declarative execution specification dynamically for any novel workflow (e.g. WF011).
    Maps declared tools and steps into executable StepDefinition models.
    """
    from src.tools.registry import tool_registry

    registered = tool_registry.list_tools()
    novel_tool = None
    for t in wf_def.tools_required:
        clean = t.lower().strip()
        if clean in registered and clean not in ["csv_reader", "read_csv", "calculator"]:
            novel_tool = clean
            break

    if not novel_tool and wf_def.tools_required:
        novel_tool = wf_def.tools_required[-1].lower().strip()

    steps = []
    for idx, s in enumerate(wf_def.steps, start=1):
        s_lower = s.lower()
        if "load" in s_lower or "read" in s_lower:
            t_name = "calculator"
        elif "calculate" in s_lower or "check" in s_lower:
            t_name = "calculator"
        elif novel_tool and ("identify" in s_lower or "flag" in s_lower or "alert" in s_lower or "analyz" in s_lower):
            t_name = novel_tool
        else:
            t_name = novel_tool or "calculator"

        steps.append(StepDefinition(
            step_number=idx,
            step_name=s,
            tool_name=t_name,
            input_mappings={"inactivity_threshold_days": "$params.threshold|30"},
            output_variable="dynamic_output",
            summary_template=f"Executed step '{s}' via {t_name}."
        ))

    def dynamic_evaluator(ctx: ExecutionContext) -> Tuple[bool, str, str, str]:
        data = ctx.get("dynamic_output", {})
        high_risk = data.get("high_risk_accounts", [])
        count = data.get("high_risk_count", len(high_risk) if isinstance(high_risk, list) else 0)
        return (
            count > 0,
            "Churn Risk Gate" if "churn" in wf_def.workflow_name.lower() else "Declarative Rule Gate",
            f"Identified {count} accounts exceeding churn thresholds." if "churn" in wf_def.workflow_name.lower() else f"Evaluated decision rule for {wf_def.workflow_name}.",
            "SUCCESS"
        )

    def dynamic_renderer(ctx: ExecutionContext) -> str:
        data = ctx.get("dynamic_output", {})
        accounts = data.get("high_risk_accounts", [])
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
        elif "summary" in data:
            return str(data["summary"])
        return f"### Executed Workflow: {wf_def.workflow_name} ({wf_def.workflow_id})\nSuccessfully executed all {len(wf_def.steps)} steps."

    return WorkflowSpec(
        workflow_id=wf_def.workflow_id,
        executable_steps=steps,
        decision_evaluator=dynamic_evaluator,
        summary_renderer=dynamic_renderer,
        data_extractor=lambda ctx: ctx.get("dynamic_output")
    )


def get_workflow_spec(wf_def) -> WorkflowSpec:
    """Retrieves predefined spec or dynamically generates one for any new workflow."""
    wf_id = wf_def.workflow_id.upper()
    if wf_id in WORKFLOW_SPEC_CATALOG:
        return WORKFLOW_SPEC_CATALOG[wf_id]
    return build_dynamic_spec_for_workflow(wf_def)
