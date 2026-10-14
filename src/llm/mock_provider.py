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
        if any(kw in query for kw in ["seo content", "product description", "generate content for this product", "write product copy", "product content", "generate content", "generate seo"]):
            params = {
                "product_name": "Ergonomic Office Chair",
                "category": "Office Furniture"
            }
            raw_text = user_request.strip()

            cat_m = re.search(r"category\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)
            mat_m = re.search(r"material\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)
            col_m = re.search(r"color\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)
            aud_m = re.search(r"audience\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)

            if cat_m:
                params["category"] = cat_m.group(1).strip()
            if mat_m:
                params["material"] = mat_m.group(1).strip()
            if col_m:
                params["color"] = col_m.group(1).strip()
            if aud_m:
                params["target_audience"] = aud_m.group(1).strip()

            name_m = re.search(r"(?:product\s*:\s*|for\s+this\s+product\s*:\s*|for\s+product\s*:\s*)([^,\n;]+)", raw_text, re.IGNORECASE)
            if name_m:
                params["product_name"] = name_m.group(1).strip()
            else:
                for_m = re.search(r"(?:for|content\s+for|description\s+for)\s+(?!this\s+product\b|a\s+product\b)([^,\n;.]+)", raw_text, re.IGNORECASE)
                if for_m:
                    extracted = for_m.group(1).strip()
                    extracted = re.sub(r"^(a|an|the)\s+", "", extracted, flags=re.IGNORECASE).strip()
                    if len(extracted) > 2 and extracted.lower() not in ["this product", "product", "me", "us"]:
                        params["product_name"] = extracted
                        if not cat_m:
                            lower_p = extracted.lower()
                            if any(w in lower_p for w in ["shoe", "sneaker", "boot", "sandal", "footwear"]):
                                params["category"] = "Footwear"
                            elif any(w in lower_p for w in ["chair", "desk", "table", "sofa", "bed"]):
                                params["category"] = "Furniture"
                            elif any(w in lower_p for w in ["phone", "laptop", "monitor", "headphone", "keyboard", "mouse", "hub", "earbud"]):
                                params["category"] = "Electronics"
                            elif any(w in lower_p for w in ["shirt", "pant", "jacket", "dress", "hoodie", "t-shirt"]):
                                params["category"] = "Apparel"
                            else:
                                params["category"] = "General Merchandise"

            return WorkflowSelection(
                workflow_id="WF004",
                workflow_name=available_workflows.get("WF004", WorkflowDefinition(workflow_id="WF004", workflow_name="Product Description Generator", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.95,
                reasoning=f"Matched intent for generating structured ecommerce product descriptions and SEO metadata for '{params['product_name']}'.",
                extracted_params=params
            )

        # 5. WF005: Customer Order Status
        if any(kw in query for kw in ["order ord-", "order status", "where is order", "track order", "tracking for"]):
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
            params = {}
            raw_text = user_request.strip()

            goal_m = re.search(r"(?:goal|objective)\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)
            if not goal_m:
                goal_m = re.search(r"brief\s+for\s+([^,\n;]+)", raw_text, re.IGNORECASE)

            dates_m = re.search(r"(?:dates?|timeline|period)\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)
            prod_m = re.search(r"(?:products?|collection)\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)
            aud_m = re.search(r"(?:audience|target)\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)
            promo_m = re.search(r"(?:promotion|discount|offer|promo)\s*:\s*([^,\n;]+)", raw_text, re.IGNORECASE)

            if goal_m:
                params["campaign_goal"] = goal_m.group(1).strip()
            elif "new collection" in query:
                params["campaign_goal"] = "Launch Spring 2026 Collection"

            if dates_m:
                params["dates"] = dates_m.group(1).strip()
            elif "new collection" in query:
                params["dates"] = "Nov 1 - Nov 30, 2026"

            if prod_m:
                params["product_list"] = prod_m.group(1).strip()
            if aud_m:
                params["target_audience"] = aud_m.group(1).strip()
            if promo_m:
                params["promotion"] = promo_m.group(1).strip()

            return WorkflowSelection(
                workflow_id="WF007",
                workflow_name=available_workflows.get("WF007", WorkflowDefinition(workflow_id="WF007", workflow_name="Marketing Campaign Brief", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.95,
                reasoning="Matched intent for creating promotional marketing campaign briefs with channel strategies and launch checklists.",
                extracted_params=params
            )

        # 8. WF008: SEO Keyword Classification
        if any(kw in query for kw in ["classify these keywords", "seo keyword", "search intent", "classify keywords", "keyword list", "classify"]):
            params = {"file_path": "data/keywords.csv"}
            kw_match = re.search(r"(?:keywords|list)\s*:\s*(.+)$", user_request.strip(), re.IGNORECASE)
            if kw_match:
                raw_kws = kw_match.group(1).split(",")
                extracted_kws = [k.strip().strip("'\"") for k in raw_kws if k.strip()]
                if len(extracted_kws) >= 2:
                    params["custom_keywords"] = extracted_kws

            return WorkflowSelection(
                workflow_id="WF008",
                workflow_name=available_workflows.get("WF008", WorkflowDefinition(workflow_id="WF008", workflow_name="SEO Keyword Classification", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.96,
                reasoning="Matched intent for categorizing keyword search intent and mapping to website landing pages.",
                extracted_params=params
            )

        # 9. WF009: Employee Task Assignment
        if ("assign" in query and "task" in query) or any(kw in query for kw in ["assign to developer", "employee task", "best available developer", "assign developer", "task assignment"]):
            known_skills = [
                "React", "Python", "FastAPI", "TypeScript", "Docker", "PostgreSQL",
                "Django", "Kafka", "Redis", "Kubernetes", "PyTorch", "LLMs",
                "LangChain", "NLP", "AWS", "Terraform", "CI/CD", "Linux",
                "Next.js", "CSS", "Tailwind", "UI/UX", "Figma", "Rust", "Solidity"
            ]
            detected_skills = []
            for skill in known_skills:
                if re.search(r"\b" + re.escape(skill) + r"\b", user_request, re.IGNORECASE):
                    detected_skills.append(skill)

            if not detected_skills:
                if "ai" in query or "machine learning" in query:
                    detected_skills = ["PyTorch", "LLMs"]
                elif "devops" in query or "cloud" in query:
                    detected_skills = ["Docker", "Kubernetes"]
                elif "frontend" in query or "ui" in query:
                    detected_skills = ["React", "UI/UX"]
                elif "backend" in query:
                    detected_skills = ["Python", "FastAPI"]
                else:
                    detected_skills = ["Python"]

            priority = "Urgent" if any(w in query for w in ["urgent", "asap", "critical", "high priority"]) else "Medium"

            return WorkflowSelection(
                workflow_id="WF009",
                workflow_name=available_workflows.get("WF009", WorkflowDefinition(workflow_id="WF009", workflow_name="Employee Task Assignment", trigger="", inputs="", steps_raw="", decision_logic="", expected_output="")).workflow_name,
                confidence=0.97,
                reasoning=f"Matched intent for ranking and allocating an urgent task ({', '.join(detected_skills)}) to best available team member.",
                extracted_params={
                    "task_description": user_request,
                    "required_skills": detected_skills,
                    "priority": priority,
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
