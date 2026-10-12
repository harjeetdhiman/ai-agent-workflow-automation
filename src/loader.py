import os
from typing import Dict, List, Optional
import openpyxl
from src.schemas import WorkflowDefinition, TestQuestion
from src.config import EXCEL_WORKFLOW_FILE


class ExcelWorkflowLoader:
    """
    Authoritative parser for loading workflow definitions and evaluation questions
    directly from the company's Excel workbook.
    """

    REQUIRED_WORKFLOW_COLUMNS = [
        "Workflow_ID",
        "Workflow_Name",
        "Trigger",
        "Inputs",
        "Steps",
        "Decision_Logic",
        "Tools_Required",
        "Expected_Output",
    ]

    REQUIRED_QUESTION_COLUMNS = [
        "Workflow_ID",
        "Test_Request",
        "What_To_Check",
    ]

    def __init__(self, excel_path: Optional[str] = None):
        self.excel_path = excel_path or EXCEL_WORKFLOW_FILE
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._test_questions: List[TestQuestion] = []
        self.load()

    def load(self) -> None:
        """Loads and validates both worksheets from the Excel file."""
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(
                f"Excel workflow file not found at '{self.excel_path}'. "
                f"Please ensure the file is present in the specified location."
            )

        wb = openpyxl.load_workbook(self.excel_path, data_only=True)

        if "Workflows" not in wb.sheetnames:
            raise ValueError(f"Workbook is missing the mandatory 'Workflows' sheet. Found: {wb.sheetnames}")

        self._load_workflows_sheet(wb["Workflows"])

        if "Test_Questions" in wb.sheetnames:
            self._load_test_questions_sheet(wb["Test_Questions"])

    def _load_workflows_sheet(self, ws) -> None:
        rows = list(ws.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            raise ValueError("The 'Workflows' worksheet is empty or missing data rows.")

        headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]

        # Verify required columns exist
        missing_cols = [col for col in self.REQUIRED_WORKFLOW_COLUMNS if col not in headers]
        if missing_cols:
            raise ValueError(f"The 'Workflows' sheet is missing required columns: {missing_cols}")

        col_idx = {col: headers.index(col) for col in self.REQUIRED_WORKFLOW_COLUMNS}

        self._workflows.clear()
        for row_num, row in enumerate(rows[1:], start=2):
            # Skip completely empty rows
            if not any(row):
                continue

            wf_id = str(row[col_idx["Workflow_ID"]]).strip() if row[col_idx["Workflow_ID"]] else ""
            if not wf_id:
                raise ValueError(f"Row {row_num} in 'Workflows' sheet has an empty 'Workflow_ID'.")

            wf_name = str(row[col_idx["Workflow_Name"]]).strip() if row[col_idx["Workflow_Name"]] else ""
            trigger = str(row[col_idx["Trigger"]]).strip() if row[col_idx["Trigger"]] else ""
            inputs = str(row[col_idx["Inputs"]]).strip() if row[col_idx["Inputs"]] else ""
            steps_raw = str(row[col_idx["Steps"]]).strip() if row[col_idx["Steps"]] else ""
            decision_logic = str(row[col_idx["Decision_Logic"]]).strip() if row[col_idx["Decision_Logic"]] else ""
            tools_raw = str(row[col_idx["Tools_Required"]]).strip() if row[col_idx["Tools_Required"]] else ""
            expected_output = str(row[col_idx["Expected_Output"]]).strip() if row[col_idx["Expected_Output"]] else ""

            # Parse steps (split by arrow character '→' or '->')
            arrow_sep = "→" if "→" in steps_raw else ("->" if "->" in steps_raw else None)
            if arrow_sep:
                steps = [s.strip() for s in steps_raw.split(arrow_sep) if s.strip()]
            else:
                steps = [steps_raw] if steps_raw else []

            # Parse tools required (split by semicolon or comma)
            tools = [t.strip() for t in tools_raw.replace(";", ",").split(",") if t.strip()]

            wf_def = WorkflowDefinition(
                workflow_id=wf_id,
                workflow_name=wf_name,
                trigger=trigger,
                inputs=inputs,
                steps_raw=steps_raw,
                steps=steps,
                decision_logic=decision_logic,
                tools_required=tools,
                expected_output=expected_output,
            )
            self._workflows[wf_id] = wf_def

    def _load_test_questions_sheet(self, ws) -> None:
        rows = list(ws.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            return

        headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
        col_idx = {col: headers.index(col) for col in self.REQUIRED_QUESTION_COLUMNS if col in headers}

        self._test_questions.clear()
        for row in rows[1:]:
            if not any(row):
                continue
            wf_id = str(row[col_idx.get("Workflow_ID", 0)]).strip() if row[col_idx.get("Workflow_ID", 0)] else ""
            test_req = str(row[col_idx.get("Test_Request", 1)]).strip() if row[col_idx.get("Test_Request", 1)] else ""
            check = str(row[col_idx.get("What_To_Check", 2)]).strip() if row[col_idx.get("What_To_Check", 2)] else ""

            if wf_id and test_req:
                self._test_questions.append(
                    TestQuestion(
                        workflow_id=wf_id,
                        test_request=test_req,
                        what_to_check=check
                    )
                )

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Returns the workflow definition for a given ID."""
        return self._workflows.get(workflow_id)

    def get_all_workflows(self) -> Dict[str, WorkflowDefinition]:
        """Returns all registered workflow definitions."""
        return dict(self._workflows)

    def get_test_questions(self) -> List[TestQuestion]:
        """Returns all test questions loaded from the Excel file."""
        return list(self._test_questions)


# Global singleton instance for easy import across modules
workflow_loader = ExcelWorkflowLoader()
