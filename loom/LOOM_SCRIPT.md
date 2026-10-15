# 🎬 3-Minute Loom Walkthrough Script: Architecture Refactoring & Verification

**Candidate:** Harjeet Singh  
**Assignment:** AI Agent Workflow Automation System  
**Target Video Duration:** 3 to 4 Minutes  
**Tool:** [Loom.com](https://www.loom.com) (Screen + Audio / Webcam)

---

## 🎯 Video Objective
Directly address and disprove the previous rejection reason:
> *"The engine relies on hardcoded WF001–WF010 handlers, and the generic fallback does not actually execute workflow steps, so new workflows require custom code."*

Demonstrate live that:
1. All hardcoded handlers have been deleted (`-1963 lines`).
2. `src/` contains **zero** hardcoded workflow IDs or domain terms.
3. Workflows and individual step sequences are driven entirely by Excel.
4. Adding an 11th or 12th workflow requires **only an Excel edit**, zero code changes.
5. All 22 test cases pass.

---

## ⏱️ Video Timeline & Screen Breakdown

| Time | What to Show on Screen | What to Say (Narration) |
| :---: | :--- | :--- |
| **0:00 - 0:45** | VS Code Terminal: `git diff --stat` & `git grep` | Direct Rejection Response & Architecture Transformation |
| **0:45 - 1:30** | Excel File: `Workflows` & `Workflow_Steps` sheets | Declarative Data Contract & Generic Tool Primitives |
| **1:30 - 2:30** | VS Code Terminal: CLI execution of WF011 & WF012 | Zero-Code Extensibility & LLM Fallback Demonstration |
| **2:30 - 3:15** | VS Code Terminal: `pytest -v` & `cli.py --benchmark` | Test Suite Verification (22/22) & Summary |

---

## 🗣️ Step-by-Step Script: Word-for-Word Narration

---

### 🔹 Part 1: Addressing the Rejection Feedback (0:00 - 0:45)

🖥️ **Screen:** Open VS Code terminal. Run:
```bash
git diff --stat origin/main
git grep -iE "WF0[0-9]{2}|inventory|restock|vendor|churn|invoice" src/
```

🗣️ **Narration:**
> *"Hello! My name is Harjeet Singh. I received the feedback on my previous submission stating that the engine relied on hardcoded WF001–WF010 handlers, and that new workflows required custom code.*
>
> *I took this critique seriously and performed a comprehensive architectural refactoring. As you can see from `git diff --stat`, I have deleted `src/workflow_specs.py` and seven monolithic tool files — eliminating over 1,900 lines of hardcoded code.*
>
> *To prove that the core engine is 100% domain-agnostic, I run this grep across the entire `src/` directory for any workflow IDs or domain keywords like 'inventory', 'restock', or 'vendor'. As you can see on the screen, there are exactly ZERO matches. The engine has zero hardcoded workflow logic."*

---

### 🔹 Part 2: The Excel Declarative Engine & Tool Primitives (0:45 - 1:30)

🖥️ **Screen:** Open `data/AI_Agent_Workflow_Assessment (1).xlsx` showing the `Workflows` and `Workflow_Steps` sheets.

🗣️ **Narration:**
> *"Instead of hardcoding workflows in Python, the system now runs on a pure Data-Driven Declarative Architecture. In this Excel file:*
>
> *1. The `Workflows` sheet defines each business process, its natural language trigger, and decision criteria.*
> *2. The new `Workflow_Steps` sheet defines the granular step-by-step pipeline: each row specifies the step order, generic tool name, JSON parameters, and context input sources.*
>
> *Our engine dispatches these steps to reusable data primitives like `filter_data`, `calculate_metrics`, `compare_records`, and `aggregate_data`. Decision logic is evaluated safely via a custom AST evaluator with zero risky `eval()` calls."*

---

### 🔹 Part 3: Live Demo: Novel Workflows & Fallback (1:30 - 2:30)

🖥️ **Screen:** Run `cli.py` in the terminal:
```bash
python cli.py --query "Track delayed supplier shipments and delivery SLA risks"
python cli.py --query "Archive legacy system transactions and sync audit logs"
```

🗣️ **Narration:**
> *"Now let's demonstrate the extensibility requirement: adding an 11th and 12th workflow with ZERO Python code changes.*
>
> *I appended WF011 ('Supplier SLA Delay Risk') and WF012 ('Legacy Data Migration') directly into the Excel workbook using openpyxl. Running `git diff --stat` proves that only the Excel binary changed.*
>
> *Now watch as I run WF011 through the CLI: the agent understands the query, selects WF011 with 98% confidence, loads order data, filters delayed shipments, and generates the report using built-in generic tools.*
>
> *Next, in WF012, step 1 references a brand-new tool — `external_legacy_mainframe_connector` — which doesn't exist in Python. Notice our execution trace: rather than crashing or faking a real tool execution, it explicitly labels the step as `executed_by: llm`. The simulated result is passed to step 2, which synthesizes the final audit report."*

---

### 🔹 Part 4: Test Suite Verification & Conclusion (2:30 - 3:15)

🖥️ **Screen:** Run the full pytest suite and benchmark:
```bash
python -m pytest tests/ -v
python cli.py --benchmark
```

🗣️ **Narration:**
> *"To ensure complete stability, I run the full test suite with `pytest -v`.*
>
> *All 22 unit, integration, and architecture tests pass — including boundary conditions, escalations, out-of-scope rejections, and dynamic registration.*
>
> *Finally, running `python cli.py --benchmark` automatically tests all 10 original workbook questions: all 10 pass with complete step execution traces and structured JSON output saved in `outputs/`.*
>
> *The system now completely satisfies the core requirement: a reusable, enterprise-grade AI workflow automation engine driven entirely by Excel. Thank you!"*
