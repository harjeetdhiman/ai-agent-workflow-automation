# 🎬 Loom Video Presentation Script & Demonstration Walkthrough

**Assignment:** AI Agent Workflow Automation System  
**Target Duration:** 5 to 7 Minutes  
**Demonstration Tools:** Terminal / CLI (`python cli.py --benchmark`) & Streamlit UI (`python -m streamlit run app.py` or `.\run_app.bat`)

---

## 📌 Video Structure Overview
| Section | Screen View | What to Run | Talking Points | Target Time |
| :---: | :--- | :--- | :--- | :---: |
| **1. Intro & Architecture** | VS Code / Architecture Diagram | Open Project Root | Objective, core problem, why NOT 10 chatbots | 0:00 - 1:00 |
| **2. Excel Dynamic Loader** | Excel File + `loader.py` | View `data/AI_Agent_Workflow_Assessment (1).xlsx` | Dynamic parsing from Excel as single source of truth | 1:00 - 2:00 |
| **3. Intent Routing & Tools** | Streamlit UI / CLI | Run `WF001` & `WF005` in UI | How NL requests map to workflows, confidence, tool calling | 2:00 - 3:30 |
| **4. Conditions & Decisions** | Streamlit UI | Run `WF002` (10% variance) & `WF009` | Deterministic logic in Python, threshold gates, escalations | 3:30 - 4:45 |
| **5. 11th Workflow Extensibility** | Streamlit Tab 3 | Click "Register & Execute WF011" | How adding an 11th workflow takes minimal changes | 4:45 - 5:45 |
| **6. Automated Tests & Wrap-Up** | Terminal | `pytest tests/ -v` | 20 automated tests passing, concluding summary | 5:45 - 6:30 |

---

## 🗣️ Step-by-Step Script with Screen Actions & Narration

### Segment 1: Introduction & Architecture Overview (0:00 - 1:00)
* **On Screen:** Show project root in VS Code and open `README.md` (Architecture diagram).
* **Verbal Script:**
  > *"Hello everyone! My name is [Your Name], and today I am demonstrating my technical assignment: the **AI Agent Workflow Automation System**.*
  >
  > *The core objective was to take 10 diverse business workflows from the company's Excel workbook and build an AI agent system that can understand natural language requests, identify the right workflow, execute the steps, handle conditions, and return structured results.*
  >
  > *A crucial architectural constraint was: **Do NOT build 10 hard-coded chatbots**. Instead, I designed a **unified, declarative execution engine**. Workflows are treated as data configurations loaded directly from Excel. Business rules, thresholds, and data operations run deterministically in Python, while the LLM handles natural language routing and structured content generation."*

---

### Segment 2: How Excel Workflows are Processed (1:00 - 2:00)
* **On Screen:** Show `data/AI_Agent_Workflow_Assessment (1).xlsx` or the "Excel Workflow Registry" tab in the Streamlit app.
* **Verbal Script:**
  > *"Let's look at how workflows are ingested. In `src/loader.py`, the `ExcelWorkflowLoader` uses openpyxl to read the `Workflows` sheet dynamically.*
  >
  > *It validates required columns—Workflow ID, Trigger, Steps, Decision Logic, Tools Required, and Expected Output. Notice that workflows are **never hardcoded in Python dictionaries**. If a business manager updates a trigger or step order in Excel, the agent reloads the new business logic automatically.*
  >
  > *We also load the `Test_Questions` sheet, which provides the 10 benchmark queries used for evaluation."*

---

### Segment 3: Intent Routing & Workflow Execution Demo (2:00 - 3:30)
* **On Screen:** Switch to the Streamlit UI (`http://localhost:8501`). Select **WF001** and click **Execute Workflow**.
* **What to Run:** Query: *"Which products need restocking?"*
* **What Appears:**
  * Selected Workflow: `WF001 - Inventory Restock Check (Confidence: 96%)`
  * Ordered Steps: 5 steps executed with green badges.
  * Tools Invoked: `csv_reader`, `calculator`, `check_inventory_restock`.
  * Output: Table of products requiring restocking.
* **Verbal Script:**
  > *"Now let's see the agent in action on our interactive Streamlit interface.*
  >
  > *I'll select the first evaluation test question: **'Which products need restocking?'**.*
  >
  > *When I click Execute, notice what happens:*
  > 1. *The router analyzes the natural language intent and maps it to `WF001: Inventory Restock Check` with 96% confidence.*
  > 2. *The engine executes all 5 ordered steps sequentially: loading inventory, comparing stock, calculating reorder quantities.*
  > 3. *Notice the tools invoked: `csv_reader` and `calculator`.*
  > 4. *The final output clearly displays which products are low on stock with exact suggested reorder units.*
  >
  > *Now let's test **WF005: Customer Order Status** with query: **'Where is order ORD-1001?'**.*
  > *The router extracts `order_id='ORD-1001'`, queries the orders store, queries real-time tracking, and returns FedEx tracking details."*

---

### Segment 4: Conditions & Error Handling (3:30 - 4:45)
* **On Screen:** Run **WF002** (*"Find products where vendor price differs by more than 10%"*) and explain the condition box. Then show an edge case (e.g., non-existent order `ORD-9999` or task assignment escalation).
* **Verbal Script:**
  > *"A critical requirement of the assignment is handling **business conditions and error states deterministically**.*
  >
  > *Let's run **WF002: Product Price Validation** with query: **'Find products where vendor price differs by more than 10%'**.*
  >
  > *Here, the price comparison and percentage variance are calculated in Python. Notice the condition evaluation box: the rule checks if `difference > 10%`. SKU-101 (with a 20% diff) is flagged as an anomaly, while SKU-104 (with 1.4% diff) is marked within tolerance.*
  >
  > *Furthermore, error handling is robust:*
  > - *If a user asks for an unknown order like `ORD-9999`, the decision logic cleanly prompts: 'No order found matching identifier. Please provide a valid order ID.'*
  > - *In **WF009: Employee Task Assignment**, if no developer has the required skill, the decision rule triggers an explicit **ESCALATE_TO_MANAGER** outcome rather than guessing.*
  > - *In **WF004: Product Description Generator**, our safeguard enforces that missing attributes like material or color are never hallucinated—they are explicitly flagged as `[Not Specified]`."*

---

### Segment 5: Supporting an 11th Workflow with Minimal Code (4:45 - 5:45)
* **On Screen:** Click on **Tab 3: 11th Workflow Extensibility** in Streamlit. Click the button: **"Register & Execute WF011 (Live Extensibility Test)"**.
* **What Appears:** Instant success banner executing `WF011: Customer Churn Risk Alert` with 5 steps and risk report.
* **Verbal Script:**
  > *"The assignment specifically asks to evaluate how the system supports an **11th workflow**.*
  >
  > *Because our architecture is decoupled and registry-driven, adding an 11th workflow—such as **WF011: Customer Churn Risk Alert**—requires zero changes to any existing workflow code:*
  > 1. *We append a row in the Excel sheet defining WF011's trigger, steps, and decision logic.*
  > 2. *If WF011 needs a specific new tool, we register it with a single `@tool_registry.register` decorator.*
  >
  > *I click this live test button, and as you can see, WF011 is dynamically recognized, all 5 steps are executed, the churn condition is checked, and high-risk accounts are returned—while all existing 10 workflows continue to function without any regression."*

---

### Segment 6: Automated Test Suite & Conclusion (5:45 - 6:30)
* **On Screen:** Open terminal and run: `python -m pytest tests/ -v`.
* **What Appears:** 20 test cases passing green (100%).
* **Verbal Script:**
  > *"To ensure enterprise-grade reliability, I built an automated test suite with **20 comprehensive pytest tests**.*
  >
  > *As you can see on screen, all 20 tests pass in 1.2 seconds:*
  > - *All 10 workbook test questions.*
  > - *Out-of-scope and ambiguous queries.*
  > - *Boundary threshold conditions.*
  > - *Escalation paths and missing inputs.*
  > - *The 11th workflow extension test.*
  >
  > *We also support a dual-mode LLM provider: OpenAI `gpt-4o-mini` for live production, and a deterministic offline provider that allows evaluators to test everything without requiring paid API keys.*
  >
  > *The complete source code, datasets, setup instructions, and tests are organized in the GitHub repository. Thank you for your time, and I look forward to discussing this project in the next stage!"*

---

## 💡 Quick Tips for Recording
1. **Resolution:** 1080p full screen or clean window capture.
2. **Audio:** Use a clear microphone; speak at a steady, confident pace.
3. **Pacing:** Let the results stay visible on screen for 2-3 seconds after executing so the reviewer can clearly read the steps and tables.
