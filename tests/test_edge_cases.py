import pytest
from src.engine import workflow_engine
from src.tools.registry import tool_registry
from src.router import WorkflowRouter
from src.schemas import StepDefinition, WorkflowDefinition


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
    """WF005: When order does not exist, return clear prompt for another identifier with NEEDS_INPUT."""
    res = workflow_engine.execute_request("Where is order ORD-9999?", override_params={"order_id": "ORD-9999"})

    assert res.selected_workflow_id == "WF005"
    assert res.status == "NEEDS_INPUT"
    assert "provide another identifier" in res.final_summary.lower()


def test_wf005_valid_order_success():
    """WF005: Valid order returns complete status, carrier name, tracking number, and delivery date."""
    res = workflow_engine.execute_request("Track customer order ORD-1001 and show me shipping details")

    assert res.selected_workflow_id == "WF005"
    assert res.status == "SUCCESS"
    assert res.final_result_data["order_id"] == "ORD-1001"
    assert res.final_result_data["order_status"] == "Shipped"
    shipment = res.final_result_data["shipment_details"]
    assert shipment["carrier"] == "FedEx"
    assert shipment["tracking_number"] == "TRK-9876543210"
    assert shipment["status"] == "In Transit"


def test_marketing_brief_missing_inputs_gate():
    """WF007: Decision logic halts early when mandatory fields (goal, dates) are missing."""
    res = workflow_engine.execute_request("Create a campaign brief.", override_params={"campaign_goal": None, "dates": None})

    assert res.selected_workflow_id == "WF007"
    assert res.status == "NEEDS_INPUT"
    assert any(c.condition_name == "Mandatory Campaign Parameter Check" and not c.outcome for c in res.conditions_evaluated)
    assert "campaign_goal" in res.final_summary or "dates" in res.final_summary


def test_wf007_with_goal_and_dates_success():
    """WF007: When goal and dates are provided, completes all 6 steps and outputs structured brief."""
    res = workflow_engine.execute_request(
        "Plan a Q4 Holiday marketing campaign brief with goal: increase revenue by 25% and dates: Nov 20 to Dec 24 2026"
    )

    assert res.selected_workflow_id == "WF007"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 6
    assert any(s.executed_by == "simulated" for s in res.steps_executed)
    assert "messaging_pillars" in res.final_result_data
    assert len(res.final_result_data["messaging_pillars"]) == 3
    assert len(res.final_result_data["channel_recommendations"]) >= 3


def test_employee_task_assignment_no_skills_mentioned():
    """WF009: When no skills are mentioned in the request, ask user for skills without escalating."""
    res = workflow_engine.execute_request("Assign the upcoming task to an employee with free capacity")

    assert res.selected_workflow_id == "WF009"
    assert res.status == "NEEDS_INPUT"
    assert len(res.steps_executed) == 1
    assert "specify the required skills" in res.final_summary.lower()


def test_employee_task_assignment_with_matching_skill_success():
    """WF009: When matching skills are provided, selects qualified employee with available capacity."""
    res = workflow_engine.execute_request(
        "Assign the backend Python developer task for building our cloud API service to an available team member"
    )

    assert res.selected_workflow_id == "WF009"
    assert res.status == "SUCCESS"
    assert res.final_result_data["assigned_employee"]["name"] == "Priya Sharma"
    assert res.final_result_data["assigned_employee"]["current_workload_pct"] == 30
    assert res.final_result_data["decision"] == "ASSIGNED"
    assert "Priya Sharma" in res.final_result_data["assignment_reasoning"]


def test_employee_task_assignment_escalation_no_skill():
    """WF009: When skills are specified but no employee in roster possesses them, escalate to manager."""
    res = workflow_engine.execute_request(
        "Assign this smart contract task",
        override_params={"required_skills": ["Rust", "Solidity_Smart_Contracts"]}
    )

    assert res.selected_workflow_id == "WF009"
    assert res.status == "FAILED"
    assert any(c.condition_name == "Capacity & Skill Allocation Rule" and not c.outcome for c in res.conditions_evaluated)
    assert "No employee in the directory possesses the required skills" in res.final_summary


def test_employee_task_assignment_escalation_at_full_capacity():
    """WF009: When all matching employees are at 100% capacity, escalate to manager."""
    res = workflow_engine.execute_request(
        "Assign this UI design task",
        override_params={"required_skills": ["Figma", "UI/UX"]}
    )

    assert res.selected_workflow_id == "WF009"
    assert res.status == "FAILED"
    assert "100% workload capacity" in res.final_summary


def test_wf011_invoice_audit_false_condition_escalates():
    """WF011: When overdue invoices exceed $2,000 threshold, False branch triggers escalation."""
    res = workflow_engine.execute_request("Audit vendor invoices and flag overdue accounts payable")

    assert res.selected_workflow_id == "WF011"
    assert res.status == "FAILED"
    assert res.final_result_data["total_overdue"] == 2470.00
    assert res.final_result_data["overdue_count"] == 3
    assert any(not c.outcome and c.branch_taken == "escalate" for c in res.conditions_evaluated)


def test_wf012_unregistered_tool_simulation():
    """WF012: Step using unregistered tool 'legal_clause_parser' executes with executed_by: simulated."""
    res = workflow_engine.execute_request("Review vendor contract terms and verify high-risk liability clauses")

    assert res.selected_workflow_id == "WF012"
    assert res.status == "SUCCESS"
    step_2 = [s for s in res.steps_executed if s.tool_name == "legal_clause_parser"][0]
    assert step_2.executed_by == "simulated"
    assert step_2.status == "SUCCESS"
    assert len(res.final_result_data["records"]) == 2


def test_unknown_tool_autonomous_fallback():
    """Autonomous fallback handles any unregistered custom tool gracefully without crashing."""
    custom_step = StepDefinition(
        step_number=1,
        step_name="Custom Unregistered Tool Step",
        tool_name="quantum_data_encryptor",
        params={"payload": "secret_key_123"},
        input_source="params",
        on_error="continue"
    )
    custom_wf = WorkflowDefinition(
        workflow_id="WF_TEST_UNKNOWN",
        workflow_name="Custom Unknown Tool Workflow",
        trigger="test unknown tool trigger",
        inputs="payload",
        steps_raw="Custom Unregistered Tool Step",
        tools_required=["quantum_data_encryptor"],
        expected_output="encrypted payload",
        executable_steps=[custom_step]
    )
    from src.loader import workflow_loader
    workflow_loader._workflows["WF_TEST_UNKNOWN"] = custom_wf

    res = workflow_engine.execute_workflow(custom_wf, "test unknown tool trigger")
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 1
    assert res.steps_executed[0].executed_by == "simulated"
    assert res.steps_executed[0].tool_name == "quantum_data_encryptor"


def test_tool_failure_and_retry():
    """Tool execution retry policy: engine retries failed tool up to configured retry count."""
    attempts = {"count": 0}

    @tool_registry.register("flaky_api_client", "Flaky tool that fails twice before succeeding.")
    def flaky_tool():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError(f"Connection timeout on attempt {attempts['count']}")
        return {"data": "success_payload", "status": "SUCCESS"}

    retry_step = StepDefinition(
        step_number=1,
        step_name="Call Flaky API",
        tool_name="flaky_api_client",
        params={},
        input_source=None,
        on_error="retry:2"
    )
    retry_wf = WorkflowDefinition(
        workflow_id="WF_TEST_RETRY",
        workflow_name="Retry Test Workflow",
        trigger="test retry logic",
        inputs="none",
        steps_raw="Call Flaky API",
        tools_required=["flaky_api_client"],
        expected_output="success",
        executable_steps=[retry_step]
    )

    res = workflow_engine.execute_workflow(retry_wf, "test retry logic")
    assert res.status == "SUCCESS"
    assert attempts["count"] == 3
    assert res.steps_executed[0].retries == 2


def test_malformed_excel_row_recovery():
    """Loader gracefully handles malformed/missing cells in Excel rows without throwing exceptions."""
    from src.loader import WorkflowLoader
    import openpyxl
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_xlsx = os.path.join(tmp_dir, "test_malformed.xlsx")
        wb = openpyxl.Workbook()
        ws_wf = wb.active
        ws_wf.title = "Workflows"
        ws_wf.append(["Workflow_ID", "Workflow_Name", "Trigger", "Inputs", "Steps", "Decision_Logic", "Tools_Required", "Expected_Output"])
        # Row with missing fields and None values
        ws_wf.append(["WF999", None, "Handle malformed request", None, None, None, None, None])

        ws_steps = wb.create_sheet("Workflow_Steps")
        ws_steps.append(["Workflow_ID", "Step_Order", "Step_Name", "Tool_Name", "Params", "Input_Source", "Condition_Expr", "On_True", "On_False", "On_Error"])
        # Malformed step row: invalid step_order string, None tool
        ws_steps.append(["WF999", "not_a_number", None, None, "{}", None, None, None, None, None])
        wb.save(tmp_xlsx)

        loader = WorkflowLoader(tmp_xlsx)
        wfs = loader.get_all_workflows()
        assert "WF999" in wfs
        assert wfs["WF999"].workflow_name == "Unnamed Workflow WF999"
        assert len(wfs["WF999"].executable_steps) >= 1


def test_router_paraphrases_suite():
    """Verify router accuracy, confidence thresholds, and ambiguity handling on new paraphrased queries."""
    router = WorkflowRouter()
    paraphrases = [
        ("WF001", "Which inventory products have low stock and need restocking?"),
        ("WF002", "Compare internal price list against vendor catalog and flag variances greater than 10%"),
        ("WF003", "Process vendor feed data file, validate required column headers and quarantine invalid product rows"),
        ("WF004", "Generate an SEO title, product description, and meta description for our ergonomic keyboard"),
        ("WF005", "What is the delivery status and carrier tracking number for customer order ORD-1002?"),
        ("WF006", "Find duplicate products in the catalog by comparing SKU and title similarity"),
        ("WF007", "Create a marketing campaign brief with goal: increase holiday sales by 25% and dates: Nov 20 to Dec 24"),
        ("WF008", "Classify search query keywords by user intent and identify high-volume commercial keywords"),
        ("WF009", "Assign the backend developer task to an employee with available workload capacity"),
        ("WF010", "Analyze agent workflow execution logs, compute error rates, and highlight slow execution steps"),
    ]

    for expected_id, query in paraphrases:
        sel = router.route(query)
        assert sel.workflow_id == expected_id, f"Query '{query}' expected {expected_id}, got {sel.workflow_id}"
        assert sel.confidence >= 0.75, f"Query '{query}' confidence {sel.confidence} is below 0.75"
        assert not sel.is_ambiguous

    # Ambiguous query test
    ambig_sel = router.route("check status")
    assert ambig_sel.is_ambiguous
    assert ambig_sel.workflow_id is None

    # Out-of-scope query test
    out_sel = router.route("Order two pepperoni pizzas and hail a cab to the airport")
    assert out_sel.workflow_id is None
    assert out_sel.confidence < 0.20
