import os
import sys
import shutil
import subprocess
import tempfile
import openpyxl
import json


def test_add_11th_workflow_with_minimal_code():
    """
    Demonstrates architectural extensibility:
    Copies repo to a fresh temp directory, edits ONLY the .xlsx via openpyxl
    to append a new workflow, verifies via 'git diff --stat' that ZERO python/code files were modified,
    and runs the standard CLI entry point (python cli.py --query "...").
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    with tempfile.TemporaryDirectory() as tmp_dir:
        target_dir = os.path.join(tmp_dir, "repo_copy")
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy2(os.path.join(base_dir, "cli.py"), os.path.join(target_dir, "cli.py"))
        shutil.copytree(os.path.join(base_dir, "src"), os.path.join(target_dir, "src"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(os.path.join(base_dir, "data"), os.path.join(target_dir, "data"))

        # 1. Initialize fresh git repo to track diffs
        subprocess.run(["git", "init"], cwd=target_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "audit@company.com"], cwd=target_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Auditor"], cwd=target_dir, check=True)
        subprocess.run(["git", "add", "-A"], cwd=target_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=target_dir, check=True, capture_output=True)

        # 2. Edit ONLY the Excel file via openpyxl (adding a novel WF013 workflow)
        excel_path = os.path.join(target_dir, "data", "AI_Agent_Workflow_Assessment (1).xlsx")
        wb = openpyxl.load_workbook(excel_path)

        ws_wf = wb["Workflows"]
        ws_wf.append([
            "WF013",
            "Customer Retention Discount Review",
            "User asks to evaluate customer account discount and retention eligibility",
            "Customer usage data, account lifetime",
            "Load account data -> Filter high-value accounts -> Calculate eligible discount -> Generate retention offer",
            "If account lifetime > 24 months, grant 20% loyalty discount",
            "read_data, filter_data, calculate_metrics, llm_generate",
            "Customer discount offer details and retention terms"
        ])

        ws_steps = wb["Workflow_Steps"]
        ws_steps.append(["WF013", 1, "Load customer accounts", "read_data", json.dumps({"file_path": "data/employees.json"}), "file:data/employees.json", None, "continue", "stop", "stop"])
        ws_steps.append(["WF013", 2, "Filter active accounts", "filter_data", json.dumps({"column": "active_tasks", "operator": ">=", "value": 1}), "step_1.output", None, "continue", "continue", "continue"])
        ws_steps.append(["WF013", 3, "Generate retention offer", "llm_generate", json.dumps({"template": "Retention Offer"}), "step_2.output", None, "continue", "continue", "continue"])

        wb.save(excel_path)

        # 3. Verify git diff --stat: PROVES ONLY THE EXCEL FILE CHANGED (zero python/code files touched!)
        diff_res = subprocess.run(["git", "diff", "--stat"], cwd=target_dir, capture_output=True, text=True, check=True)
        print("\n=== GIT DIFF --STAT IN TEMP REPO PROVING ONLY EXCEL CHANGED ===")
        print(diff_res.stdout)
        assert "AI_Agent_Workflow_Assessment (1).xlsx" in diff_res.stdout
        assert ".py" not in diff_res.stdout, "Violation: Code files were modified when adding workflow!"

        # 4. Run through normal CLI entry point
        query = "evaluate customer account discount and retention eligibility"
        cli_res = subprocess.run(
            [sys.executable, "cli.py", "--query", query],
            cwd=target_dir,
            capture_output=True,
            text=True
        )

        output = cli_res.stdout
        print("\n=== CLI EXECUTION OUTPUT FOR NOVEL EXCEL-ONLY WORKFLOW ===")
        print(output)

        assert cli_res.returncode == 0
        assert "Selected Workflow:     WF013 - Customer Retention Discount Review" in output
        assert "Execution Status:      SUCCESS" in output
        assert "1. [OK] Load customer accounts" in output
        assert "2. [OK] Filter active accounts" in output
        assert "3. [OK] Generate retention offer" in output
