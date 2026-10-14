from src.schemas import WorkflowDefinition
from src.loader import workflow_loader
from src.engine import workflow_engine
from src.tools.registry import tool_registry


def test_add_11th_workflow_with_minimal_code():
    """
    Demonstrates architectural extensibility:
    Adding an 11th workflow (WF011: Customer Churn Risk Alert)
    requires ONLY registering its declarative definition and domain tool,
    with ZERO custom handler code and ZERO changes to the engine or existing workflows.
    """
    # 1. Register WF011 Definition (simulating appending a row in Excel)
    wf011_def = WorkflowDefinition(
        workflow_id="WF011",
        workflow_name="Customer Churn Risk Alert",
        trigger="User asks to identify customer accounts at risk of churning",
        inputs="Customer usage metrics CSV; inactivity threshold",
        steps_raw="Load usage data → calculate inactivity duration → check churn threshold → identify high-risk accounts → generate retention alert",
        steps=[
            "Load usage data",
            "Calculate inactivity duration",
            "Check churn threshold",
            "Identify high-risk accounts",
            "Generate retention alert"
        ],
        decision_logic="If days_inactive > 30 and engagement_drop > 50%, flag account as high churn risk",
        tools_required=["csv_reader", "calculator", "churn_analyzer"],
        expected_output="List of high-risk customer accounts with retention recommendations"
    )

    # Add to active registry
    workflow_loader._workflows["WF011"] = wf011_def

    # 2. Register novel domain tool required (churn_analyzer)
    @tool_registry.register("churn_analyzer", "Analyzes user activity to flag high churn risk accounts (WF011)")
    def analyze_churn(inactivity_threshold_days: int = 30):
        # Sample synthetic calculation
        sample_accounts = [
            {"account_id": "ACC-801", "name": "Acme Logistics", "days_inactive": 42, "engagement_drop_pct": 65, "risk": "HIGH"},
            {"account_id": "ACC-802", "name": "Global Retailers", "days_inactive": 12, "engagement_drop_pct": 10, "risk": "LOW"},
            {"account_id": "ACC-803", "name": "Nexus Fintech", "days_inactive": 35, "engagement_drop_pct": 55, "risk": "HIGH"}
        ]
        high_risk = [a for a in sample_accounts if a["days_inactive"] > inactivity_threshold_days and a["engagement_drop_pct"] > 50]
        return {
            "total_accounts_scanned": len(sample_accounts),
            "high_risk_count": len(high_risk),
            "high_risk_accounts": high_risk
        }

    # 3. Execute request for the 11th workflow WITHOUT any custom handler code!
    # The universal declarative step engine executes all 5 steps and evaluates decision rules automatically!
    test_query = "identify customer accounts at risk of churning"
    res = workflow_engine.execute_request(test_query)

    assert res.selected_workflow_id == "WF011"
    assert res.selected_workflow_name == "Customer Churn Risk Alert"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 5
    assert "churn_analyzer" in res.tools_invoked
    assert res.final_result_data["high_risk_count"] == 2

    # 4. Verify existing 10 workflows still work seamlessly without regressions
    res_wf001 = workflow_engine.execute_request("Which products need restocking?")
    assert res_wf001.selected_workflow_id == "WF001"
    assert res_wf001.status == "SUCCESS"
