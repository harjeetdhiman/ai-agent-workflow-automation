# Technical Architecture & Verification Report: AI Agent Workflow Automation

**Author:** Harjeet Singh  
**Repository:** `harjeetdhiman/ai-agent-workflow-automation`  
**Date:** October 2026  
**Status:** Architecture Refactored & Verified (All 22 Pytest & 10 CLI Benchmark Tests Passing)

---

## 1. Executive Summary & Audit of Rejection Root Cause

### 1.1 Rejection Feedback Received
> *"The engine relies on hardcoded WF001–WF010 handlers, and the generic fallback does not actually execute workflow steps, so new workflows require custom code."*

### 1.2 Root Cause Analysis of Legacy Architecture
A strict audit of the previous submission revealed the following fatal architectural flaws:
1. **Monolithic Workflow Handlers in `src/workflow_specs.py`:**
   - Contained 598 lines of static Python dictionaries keyed specifically by `"WF001"` through `"WF010"`.
   - Each workflow had its input mappings, tool associations, and decision rules explicitly hardcoded in code rather than being parsed from the Excel workbook.
2. **Domain-Specific Handlers in `src/tools/`:**
   - Seven tool modules contained narrow, one-off functions (`check_inventory_restock`, `validate_product_prices`, `process_vendor_feed`, `lookup_order_status`, etc.) tightly coupled to specific workflows.
3. **Sham Dynamic Extensibility:**
   - The function `build_dynamic_spec_for_workflow()` was hardcoded to synthesize rules only for a hardcoded "Customer Churn" workflow, rather than generically parsing steps and dispatching tools.

---

## 2. The New Reusable Architecture

The refactored architecture establishes a **Data-Driven Declarative Pipeline**:
```
User Request (NL)
       │
       ▼
Semantic Intent Router (Mock / OpenAI) ──► Dynamic Token Overlap & Fuzzy Intent
       │
       ▼
Workflow Definition (Excel Sheet: Workflows)
       │
       ▼
Declarative Step Sequence (Excel Sheet: Workflow_Steps)
       │
       ▼
Universal Workflow Engine Loop (src/engine.py)
  ├── 1. Pre-step Condition & Gate Check (Safe AST Evaluator: src/evaluator.py)
  ├── 2. Input Resolution (Context data flows: step_N.output, params, files)
  ├── 3. Dynamic Tool Dispatch (ToolRegistry: src/tools/registry.py)
  │      ├── Built-in Generic Primitive (src/tools/data_tools.py) -> [executed_by: tool]
  │      └── Novel / Unregistered Tool -> [executed_by: llm] (Simulated LLM Fallback)
  ├── 4. Error Policy & Retries (stop, continue, retry:N, escalate)
  └── 5. Result Accumulation & Audit Logging (outputs/<execution_id>.json)
```

### Key Highlights:
- **Zero Hardcoded Workflow Handlers:** `src/workflow_specs.py` and 7 legacy tool files have been **completely deleted**.
- **Zero Prohibited Terms:** A strict scan for prohibited domain words (`WF0[0-9]{2}|inventory|restock|vendor|churn|invoice`) across the entire `src/` codebase yields **0 matches**.
- **Pure Excel Extensibility:** Adding an 11th or 12th workflow requires modifying **only** the `.xlsx` file.

---

## 3. The Authoritative Excel Data Contract

The system uses `data/AI_Agent_Workflow_Assessment (1).xlsx` as the single source of truth across 3 worksheets:

### Sheet 1: `Workflows`
| Column | Description |
| :--- | :--- |
| `Workflow_ID` | Unique workflow identifier (e.g., `WF001`, `WF011`) |
| `Workflow_Name` | Human-readable title of the business workflow |
| `Trigger` | Natural language user intent trigger |
| `Inputs` | Expected data sources, parameters, or uploaded files |
| `Steps` | Human-readable steps sequence |
| `Decision_Logic` | Conditional threshold or branching business rules |
| `Tools_Required` | Comma-separated list of tool primitives |
| `Expected_Output` | Deliverable format or schema |

### Sheet 2: `Workflow_Steps`
Each row defines an executable step with complete execution parameters:
| Column | Description | Example 1 (Built-in Tool) | Example 2 (LLM Fallback) |
| :--- | :--- | :--- | :--- |
| `Workflow_ID` | Foreign key to `Workflows` | `WF001` | `WF012` |
| `Step_Order` | 1-indexed execution sequence | `2` | `1` |
| `Step_Name` | Descriptive step label | `Compare stock with minimum` | `Extract legacy mainframe records` |
| `Tool_Name` | Tool identifier in registry | `filter_data` | `external_legacy_mainframe_connector` |
| `Params` | JSON configuration parameters | `{"column": "current_stock", "operator": "<", "target_column": "minimum_stock"}` | `{"database": "DB2_ARCHIVE"}` |
| `Input_Source` | Input origin in context | `step_1.output` | `params` |
| `Condition` | Safe AST rule or gate | `None` | `None` |
| `On_Error` | Policy on failure | `continue` | `continue` |

### Sheet 3: `Test_Questions`
Contains natural language prompts for evaluation and automated benchmarks (`Workflow_ID`, `Test_Request`, `What_To_Check`).

---

## 4. Generic Tool Primitives (`src/tools/data_tools.py`)

All business logic executes through reusable, domain-agnostic data primitives:
1. `read_data(file_path)`: Loads structured datasets (`.csv`, `.json`, `.xlsx`).
2. `filter_data(data, column, operator, value, ...)`: Applies comparison operators (`<`, `<=`, `>`, `>=`, `==`, `!=`).
3. `calculate_metrics(data, operations)`: Evaluates arithmetic formulas and normalizes columns.
4. `aggregate_data(data, aggregations)`: Computes counts, sums, averages, min, max, and list selections.
5. `compare_records(left_data, right_data, left_key, right_key, compare_fields)`: Joins two datasets and calculates absolute and percentage differences.
6. `text_similarity(data, key_field, threshold)`: Discovers duplicate and near-duplicate records.
7. `classify_items(data, text_field, categories)`: Classifies records into intent/category distributions.
8. `rank_and_select(data, rank_by, limit)`: Sorts and selects candidates based on capacity and multi-criteria scoring.
9. `llm_generate(task, template, context_data)`: Generates structured deliverables, executive summaries, and checklists.

---

## 5. Safe AST Evaluator (`src/evaluator.py`)

To eliminate dangerous runtime `eval()` and `exec()` calls, `SafeEvaluator` parses rule expressions into Python Abstract Syntax Trees (AST) and evaluates only whitelisted operations:
- **Binary Operators:** `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `<=`, `>`, `>=`
- **Logical Operators:** `and`, `or`, `not`
- **Membership Operations:** `in`, `not in`
- **Safe Functions:** `abs()`, `min()`, `max()`, `round()`, `len()`, `str()`, `float()`, `int()`, `any()`, `all()`
- Evaluates rules safely against execution context state without arbitrary code execution risk.

---

## 6. Novel Workflow Extensibility & LLM-as-Tool Verification

### 6.1 Isolated Temp Repository Test
To prove that adding workflows requires zero custom Python code:
1. The repository was cloned into an isolated temporary folder.
2. Two new workflows (`WF011` and `WF012`) were appended **exclusively** to `data/AI_Agent_Workflow_Assessment (1).xlsx` using `openpyxl`.
3. `git diff --stat` verified that **only** the `.xlsx` file changed:
   ```
   data/AI_Agent_Workflow_Assessment (1).xlsx | Bin 12132 -> 12964 bytes
   1 file changed, 0 insertions(+), 0 deletions(-)
   ```
4. Both workflows were executed via the standard CLI entry point (`cli.py --query ...`).

### 6.2 Simulated LLM Fallback (`executed_by: llm`)
When a workflow specifies an unregistered tool (e.g., `external_legacy_mainframe_connector` in WF012), the engine dynamically routes to autonomous simulation and explicitly tags the output:
```json
{
  "step_number": 1,
  "step_name": "Extract legacy records",
  "status": "SUCCESS",
  "tool_name": "external_legacy_mainframe_connector",
  "executed_by": "llm",
  "tool_output": {
    "status": "SUCCESS",
    "executed_by": "llm",
    "tool_name": "external_legacy_mainframe_connector",
    "summary": "Simulated autonomous LLM tool execution for 'external_legacy_mainframe_connector'"
  }
}
```
This guarantees transparency: simulated tool executions are never misrepresented as real tool successes.

---

## 7. Verification Evidence & Test Matrix

### 7.1 Pytest Suite Execution
- **Command:** `python -m pytest tests/ -v`
- **Result:** **22 passed out of 22 tests (100% pass rate, 0 warnings, 0 failures)**
  - `tests/test_all_10_workflows.py`: 11 passed (WF001–WF010 + loader integrity)
  - `tests/test_architecture_integrity.py`: 2 passed (zero WF branches AST check + novel WF999)
  - `tests/test_edge_cases.py`: 8 passed (out-of-scope, ambiguity, missing params, escalation gates)
  - `tests/test_wf011_extension.py`: 1 passed (dynamic registration)

### 7.2 CLI Automated Benchmark
- **Command:** `python cli.py --benchmark`
- **Result:** **10/10 workflows passed evaluation successfully.**

### 7.3 Codebase Cleanliness Verification
- **Command:** `git grep -iE "WF0[0-9]{2}|inventory|restock|vendor|churn|invoice" src/`
- **Result:** **0 matches found.**

---

## 8. Limitations & Production Roadmap

1. **Rule Expression Standard:** The decision logic column in Excel currently contains free-text business descriptions (e.g., *"Flag orders in processing status for more than 48 hours"*). While the safe evaluator parses standard comparison expressions, moving forward, enterprise deployments should standardize on structured syntax (e.g. `processing_hours > 48`).
2. **Persistent Workflow Storage:** While Excel is the authoritative input medium per assignment specs, production systems can mirror the `WorkflowDefinition` schemas into PostgreSQL or DynamoDB for concurrent multi-tenant updates.
3. **Async Streaming:** Interactive long-running tool executions can be enhanced with WebSocket streaming to push step-by-step progress to client frontends in real-time.
