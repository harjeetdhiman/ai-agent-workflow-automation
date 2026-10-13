import re
from typing import Dict
from src.schemas import WorkflowDefinition, WorkflowSelection
from src.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic, zero-cost LLM Provider designed for local automated testing,
    continuous integration, and offline evaluation.
    Matches natural-language intents against the Excel-defined triggers and extracts parameters.
    """

    def route_request(
        self,
        user_request: str,
        available_workflows: Dict[str, WorkflowDefinition]
    ) -> WorkflowSelection:
        query = user_request.strip().lower()

        # Check for ambiguity
        if query in ["check status", "show report", "process data", "analyze"]:
            return WorkflowSelection(
                workflow_id=None,
                workflow_name=None,
                confidence=0.35,
                reasoning="The request is ambiguous and could match multiple workflows (Order Status, Performance Report, or Vendor Processing).",
                is_ambiguous=True,
                clarification_prompt="Could you specify whether you want to check an Order Status (WF005), a Workflow Performance Report (WF010), or Process a Vendor File (WF003)?"
            )

        # 1. WF001: Inventory Restock
        if any(kw in query for kw in ["restock", "restocking", "low stock", "inventory level", "stock threshold"]):
            return WorkflowSelection(
                workflow_id="WF001",
                workflow_name=available_workflows.get("WF001", WorkflowDefinition(workflow_id="WF001", workflow_name="Inventory Restock Check", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.96,
                reasoning="Matched intent for identifying products below minimum stock thresholds and restock calculations.",
                extracted_params={"threshold": 10}
            )

        # 2. WF002: Product Price Validation
        if any(kw in query for kw in ["vendor price", "price differ", "price validation", "validate price", "price difference"]):
            # Extract threshold percentage if mentioned (e.g. "more than 10%")
            thresh_match = re.search(r"(\d+(\.\d+)?)\s*%", query)
            variance = float(thresh_match.group(1)) / 100.0 if thresh_match else 0.10
            return WorkflowSelection(
                workflow_id="WF002",
                workflow_name=available_workflows.get("WF002", WorkflowDefinition(workflow_id="WF002", workflow_name="Product Price Validation", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.95,
                reasoning="Matched intent for comparing internal retail catalog prices against vendor pricing lists.",
                extracted_params={"variance_threshold": variance}
            )

        # 3. WF003: Vendor File Processing
        if any(kw in query for kw in ["vendor spreadsheet", "vendor file", "process vendor", "invalid row", "clean vendor"]):
            return WorkflowSelection(
                workflow_id="WF003",
                workflow_name=available_workflows.get("WF003", WorkflowDefinition(workflow_id="WF003", workflow_name="Vendor File Processing", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.97,
                reasoning="Matched intent for reading, validating, and sanitizing vendor product data feeds.",
                extracted_params={"file_path": "data/vendor_raw_feed.csv"}
            )

        # 4. WF004: Product Description Generator
        if any(kw in query for kw in ["seo content", "product description", "generate content for this product", "write product copy", "product content"]):
            # Try to extract product details from query if provided
            return WorkflowSelection(
                workflow_id="WF004",
                workflow_name=available_workflows.get("WF004", WorkflowDefinition(workflow_id="WF004", workflow_name="Product Description Generator", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.94,
                reasoning="Matched intent for generating structured ecommerce product descriptions and SEO metadata.",
                extracted_params={
                    "product_name": "Ergonomic Mesh Chair",
                    "category": "Office Furniture"
                }
            )

        # 5. WF005: Customer Order Status
        if any(kw in query for kw in ["order ord-", "order status", "where is order", "track order", "tracking for"]):
            # Extract order ID like ORD-1001 or email
            order_match = re.search(r"ord-\d+", query, re.IGNORECASE)
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", query)
            order_id = order_match.group(0).upper() if order_match else None
            email = email_match.group(0) if email_match else None

            params = {}
            if order_id:
                params["order_id"] = order_id
            if email:
                params["customer_email"] = email

            return WorkflowSelection(
                workflow_id="WF005",
                workflow_name=available_workflows.get("WF005", WorkflowDefinition(workflow_id="WF005", workflow_name="Customer Order Status", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.98,
                reasoning="Matched intent for looking up customer order fulfillment status and carrier tracking details.",
                extracted_params=params
            )

        # 6. WF006: Duplicate Product Detection
        if any(kw in query for kw in ["duplicate product", "duplicate", "redundant product", "catalog duplicate"]):
            return WorkflowSelection(
                workflow_id="WF006",
                workflow_name=available_workflows.get("WF006", WorkflowDefinition(workflow_id="WF006", workflow_name="Duplicate Product Detection", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.95,
                reasoning="Matched intent for detecting duplicate listings in catalog via SKU matching and attribute similarity.",
                extracted_params={"similarity_threshold": 0.75}
            )

        # 7. WF007: Marketing Campaign Brief
        if any(kw in query for kw in ["campaign brief", "marketing brief", "create a campaign", "promotion brief"]):
            # Check if dates or goal are present
            params = {}
            if "collection" in query:
                params["campaign_goal"] = "Launch Spring 2026 Collection"
            return WorkflowSelection(
                workflow_id="WF007",
                workflow_name=available_workflows.get("WF007", WorkflowDefinition(workflow_id="WF007", workflow_name="Marketing Campaign Brief", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.95,
                reasoning="Matched intent for creating promotional marketing campaign briefs with channel strategies and launch checklists.",
                extracted_params=params
            )

        # 8. WF008: SEO Keyword Classification
        if any(kw in query for kw in ["classify these keywords", "seo keyword", "search intent", "classify keywords", "keyword list"]):
            return WorkflowSelection(
                workflow_id="WF008",
                workflow_name=available_workflows.get("WF008", WorkflowDefinition(workflow_id="WF008", workflow_name="SEO Keyword Classification", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.96,
                reasoning="Matched intent for categorizing keyword search intent and mapping to website landing pages.",
                extracted_params={"file_path": "data/keywords.csv"}
            )

        # 9. WF009: Employee Task Assignment
        if ("assign" in query and "task" in query) or any(kw in query for kw in ["assign to developer", "employee task", "best available developer", "assign developer", "task assignment"]):
            return WorkflowSelection(
                workflow_id="WF009",
                workflow_name=available_workflows.get("WF009", WorkflowDefinition(workflow_id="WF009", workflow_name="Employee Task Assignment", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.97,
                reasoning="Matched intent for ranking and allocating an urgent task to an employee based on skills and capacity.",
                extracted_params={
                    "task_description": user_request,
                    "required_skills": ["Python"],
                    "priority": "Urgent",
                    "deadline": "2026-10-15"
                }
            )

        # 10. WF010: Workflow Performance Report
        if any(kw in query for kw in ["failing most often", "performance report", "workflow performance", "execution log", "workflow metrics", "failing workflow"]):
            return WorkflowSelection(
                workflow_id="WF010",
                workflow_name=available_workflows.get("WF010", WorkflowDefinition(workflow_id="WF010", workflow_name="Workflow Performance Report", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.98,
                reasoning="Matched intent for calculating workflow reliability metrics, error breakdowns, and performance optimization flags.",
                extracted_params={"file_path": "data/execution_logs.csv"}
            )

        # Dynamic check for any registered 11th workflow
        for w_id, w_def in available_workflows.items():
            if w_id not in [f"WF00{i}" for i in range(1, 10)] and w_id != "WF010":
                # Check if trigger words match
                trig_words = [w.lower() for w in w_def.trigger.split() if len(w) > 3]
                if any(tw in query for tw in trig_words) or w_def.workflow_name.lower() in query:
                    return WorkflowSelection(
                        workflow_id=w_id,
                        workflow_name=w_def.workflow_name,
                        confidence=0.91,
                        reasoning=f"Matched trigger condition for dynamically registered workflow {w_id} ({w_def.workflow_name}).",
                        extracted_params={}
                    )

        # Unrecognized / Unsupported query
        return WorkflowSelection(
            workflow_id=None,
            workflow_name=None,
            confidence=0.10,
            reasoning="The user request does not match any of the registered business workflows.",
            is_ambiguous=False,
            clarification_prompt="I could not identify a matching business workflow. Please choose from: Inventory Restock, Price Validation, Vendor File Processing, Product Description, Order Status, Duplicate Detection, Marketing Brief, SEO Keywords, Task Assignment, or Performance Report."
        )

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        """Deterministic mock text generation."""
        if "product description" in prompt.lower() or "seo" in prompt.lower():
            return (
                "Premium Ergonomic Solution: Designed for comfort and durability. "
                "Featuring adaptive support and high-grade build quality."
            )
        return "Generated response based on provided business parameters."
