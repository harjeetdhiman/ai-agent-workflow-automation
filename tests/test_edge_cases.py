from src.engine import workflow_engine
from src.tools.registry import tool_registry


def test_unsupported_out_of_scope_query():
    """System rejects out-of-scope requests gracefully without crashing or hallucinating a workflow."""
    query = "Order a pizza and book flight tickets to Paris."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id is None
    assert res.status == "FAILED"
    assert "No matching workflow" in (res.error_message or res.final_summary)


def test_ambiguous_request_clarification():
    """Ambiguous requests trigger a clarification prompt with status NEEDS_INPUT."""
    query = "check status"
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id is None
    assert res.status == "NEEDS_INPUT"
    assert "specify" in res.final_summary.lower()


def test_order_lookup_not_found():
    """WF005: When order does not exist, return clear prompt for another identifier."""
    res = workflow_engine.execute_request("Where is order ORD-9999?", override_params={"order_id": "ORD-9999"})

    assert res.selected_workflow_id == "WF005"
    assert res.status == "FAILED"
    assert "No order found matching identifier 'ORD-9999'" in res.final_summary


def test_marketing_brief_missing_inputs_gate():
    """WF007: Decision logic halts early when mandatory fields (goal, dates) are missing."""
    res = workflow_engine.execute_request("Create a campaign brief.", override_params={"campaign_goal": None, "dates": None})

    assert res.selected_workflow_id == "WF007"
    assert res.status == "NEEDS_INPUT"
    assert any(c.condition_name == "Mandatory Campaign Parameter Check" and not c.outcome for c in res.conditions_evaluated)
    assert "campaign_goal" in res.final_summary or "dates" in res.final_summary


def test_employee_task_assignment_escalation_no_skill():
    """WF009: When no employee has the required skill, escalate to manager."""
    res = workflow_engine.execute_request(
        "Assign this task",
        override_params={"required_skills": ["Rust", "Solidity_Smart_Contracts"]}
    )

    assert res.selected_workflow_id == "WF009"
    assert res.status == "FAILED"
    assert any(c.condition_name == "Capacity & Skill Allocation Rule" and not c.outcome for c in res.conditions_evaluated)
    assert "No employee in the directory possesses the required skills" in res.final_summary


def test_employee_task_assignment_escalation_at_full_capacity():
    """WF009: When all matching employees are at 100% capacity, escalate to manager."""
    # Elena Rostova is the only UI/Figma specialist and is at 100% capacity
    res = workflow_engine.execute_request(
        "Assign this UI design task",
        override_params={"required_skills": ["Figma", "UI/UX"]}
    )

    assert res.selected_workflow_id == "WF009"
    assert res.status == "FAILED"
    assert "100% workload capacity" in res.final_summary


def test_inventory_boundary_threshold():
    """WF001: Item with stock exactly equal to threshold must NOT be flagged for restock."""
    res = tool_registry.execute("check_inventory_restock", file_path="data/inventory.csv")
    restock_skus = [it["sku"] for it in res["restock_list"]]
    # SKU-105: current_stock = 10, minimum_stock = 10 -> rule: current < min -> False
    assert "SKU-105" not in restock_skus


def test_price_validation_boundary():
    """WF002: Variance exactly at 10.0% boundary condition."""
    # SKU-105: internal 199.99, vendor 219.99 -> abs(20.00)/199.99 = 10.0005% -> boundary
    res = tool_registry.execute("validate_product_prices", variance_threshold=0.10)
    assert "exceptions" in res
    assert res["total_matched"] > 0
