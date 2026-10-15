from src.engine import workflow_engine
from src.loader import workflow_loader


def test_excel_loader_integrity():
    """Verify that all 10 workflows and test questions load correctly from Excel."""
    wfs = workflow_loader.get_all_workflows()
    assert len(wfs) >= 10, f"Expected at least 10 workflows, found {len(wfs)}"
    for i in range(1, 11):
        wf_id = f"WF{i:03d}"
        assert wf_id in wfs, f"Workflow {wf_id} missing from Excel registry"
        wf = wfs[wf_id]
        assert len(wf.steps) > 0, f"Workflow {wf_id} has no steps"
        assert len(wf.tools_required) > 0, f"Workflow {wf_id} has no tools declared"

    tqs = workflow_loader.get_test_questions()
    assert len(tqs) >= 10, f"Expected 10 test questions, found {len(tqs)}"


def test_wf001_inventory_restock():
    """WF001: Which products need restocking?"""
    query = "Which products need restocking?"
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF001"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 5
    assert "csv_reader" in res.tools_invoked
    assert "calculator" in res.tools_invoked
    assert res.final_result_data["products_needing_restock_count"] > 0
    # Boundary check: Ensure SKU-105 (current 10 == min 10) is NOT in restock list (rule: current < min)
    restock_skus = [it["sku"] for it in res.final_result_data["restock_list"]]
    assert "SKU-105" not in restock_skus
    # SKU-103 (stock 0) must be flagged
    assert "SKU-103" in restock_skus


def test_wf002_price_validation():
    """WF002: Find products where vendor price differs by more than 10%."""
    query = "Find products where vendor price differs by more than 10%."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF002"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 5
    assert res.final_result_data["exceptions_flagged_count"] > 0
    # SKU-101 (diff 20%) must be flagged
    flagged_skus = [e["sku"] for e in res.final_result_data["exceptions"]]
    assert "SKU-101" in flagged_skus
    # SKU-104 (diff 1.4%) must NOT be flagged
    assert "SKU-104" not in flagged_skus


def test_wf003_vendor_file_processing():
    """WF003: Process this vendor spreadsheet and show invalid rows."""
    query = "Process this vendor spreadsheet and show invalid rows."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF003"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 6
    assert res.final_result_data["invalid_rows_count"] > 0
    # Must report invalid rows lacking SKU or product name
    invalid_report = res.final_result_data["invalid_rows_report"]
    assert any("SKU" in str(inv["errors"]) for inv in invalid_report)
    assert any("Product Name" in str(inv["errors"]) for inv in invalid_report)


def test_wf004_product_description_generator():
    """WF004: Generate SEO content for this product."""
    query = "Generate SEO content for this product."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF004"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 5
    data = res.final_result_data
    # Verify hallucination prevention rule: missing attributes explicitly audited
    assert "missing_attributes_flagged" in data["attribute_audit"]
    # Check SEO length constraints
    assert data["seo_title_length"] <= 60
    assert data["meta_description_length"] <= 160


def test_wf005_customer_order_status():
    """WF005: Where is order ORD-1001?"""
    query = "Where is order ORD-1001?"
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF005"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 5
    data = res.final_result_data
    assert data["order_id"] == "ORD-1001"
    assert data["order_status"] == "Shipped"
    assert data["shipment_details"]["carrier"] == "FedEx"
    assert data["shipment_details"]["tracking_number"] == "TRK-9876543210"


def test_wf006_duplicate_product_detection():
    """WF006: Find likely duplicate products in the catalog."""
    query = "Find likely duplicate products in the catalog."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF006"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 6
    data = res.final_result_data
    assert data["definite_duplicates_count"] >= 1
    assert data["possible_duplicates_count"] >= 1


def test_wf007_marketing_campaign_brief():
    """WF007: Create a campaign brief for the new collection."""
    query = "Create a campaign brief for the new collection with goal of $50k revenue from Nov 20 to Nov 30 2026."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF007"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 6
    data = res.final_result_data
    assert len(data["messaging_pillars"]) == 3
    assert len(data["channel_recommendations"]) >= 3
    assert len(data["launch_checklist"]) >= 4


def test_wf008_seo_keyword_classification():
    """WF008: Classify these keywords and map them to pages."""
    query = "Classify these keywords and map them to pages."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF008"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 6
    data = res.final_result_data
    assert data["duplicates_removed"] >= 1
    # Check that search intents are populated
    intents = data["intent_distribution"]
    assert "Transactional" in intents
    assert "Commercial" in intents
    assert "Informational" in intents


def test_wf009_employee_task_assignment():
    """WF009: Assign this urgent task to the best available developer."""
    query = "Assign this urgent task to the best available developer."
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF009"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 6
    data = res.final_result_data
    assert data["decision"] == "ASSIGNED"
    assert "assigned_employee" in data
    assert data["assigned_employee"]["name"] is not None


def test_wf010_workflow_performance_report():
    """WF010: Which workflows are failing most often?"""
    query = "Which workflows are failing most often?"
    res = workflow_engine.execute_request(query)

    assert res.selected_workflow_id == "WF010"
    assert res.status == "SUCCESS"
    assert len(res.steps_executed) == 6
    data = res.final_result_data
    assert data["total_executions_analyzed"] > 0
    assert data["flagged_workflows_count"] >= 1
    # WF003 should be flagged due to >10% failure rate in logs
    flagged_ids = [w["workflow_id"] for w in data["flagged_workflows"]]
    assert "WF003" in flagged_ids
