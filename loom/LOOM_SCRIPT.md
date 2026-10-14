# 🎬 Loom Video Complete Walkthrough Script (Hinglish + English)

**Assignment:** AI Agent Workflow Automation System  
**Target Duration:** 5 to 7 Minutes  
**Video Recording Tool:** [Loom.com](https://www.loom.com) (Screen + Camera or Screen Only)

---

## 🛠️ Step 0: Recording Shuru Karne Se Pehle Kya Taiyar Rakhna Hai?

Apne laptop par **2 Windows** open rakhein:
1. **Window 1 (Browser):** Streamlit Web App khol kar rakhein: `http://localhost:8501`  
   *(Agar band hai toh terminal me `python -m streamlit run app.py` chalayein ya `run_app.bat` double-click karein)*
2. **Window 2 (VS Code / Terminal):** Project folder open rakhein taaki aap files aur tests dikha sakein.

---

## ⏱️ Video Timeline & Screen Breakdown

| Time | Kaunsi Screen Dikhani Hai | Kya Bolna Hai (Key Topics) |
| :---: | :--- | :--- |
| **0:00 - 1:15** | VS Code / `README.md` (Architecture Diagram) | Introduction, problem statement, aur architecture (Kyu yeh 10 alag chatbots nahi hai). |
| **1:15 - 2:15** | Streamlit Tab 2 / Excel File | Excel dynamic ingestion & Synthetic data explanation. |
| **2:15 - 3:00** | VS Code (`src/llm/`) | Dual-Mode LLM explanation (OpenAI integration + Offline Mock Intent Engine). |
| **3:00 - 4:45** | Streamlit Tab 1 (Live Demo) | Live execution: **WF001** (Inventory), **WF002** (Price Validation), **WF005** (Order Status). |
| **4:45 - 5:45** | Streamlit Tab 3 (Extensibility) | Live 11th Workflow (`WF011`) dynamic registration demo. |
| **5:45 - 6:30** | Terminal / Command Prompt | Automated Pytest (`20/20 passed`) & CLI benchmark (`10/10 passed`). |

---

## 🗣️ Step-by-Step Script: "Ab Yeh Kholo Aur Yeh Bolo"

---

### 🔹 Part 1: Introduction & Architecture (0:00 - 1:15)

🖥️ **Screen Par Kya Dikhana Hai:**  
VS Code kholo aur [`README.md`](../README.md) ka **Architecture Diagram** screen par dikhao.

🗣️ **Aapko Kya Bolna Hai (Narration):**
> *"Hello everyone! My name is **Harjeet Singh**, and today I am presenting my technical assignment: the **AI Agent Workflow Automation System**.*
>
> *Company ne hume ek Excel file di thi jisme **10 diverse business workflows** the — jaise inventory restock, price validation, vendor cleaning, order tracking, aur task assignment.*
>
> *Assignment ka sabse critical requirement yeh tha: **'Do NOT build 10 separate hard-coded chatbots. Build a reusable and scalable agent architecture where adding an 11th workflow requires minimal code changes.'***
>
> *Maine ise solve karne ke liye ek **Unified Declarative Execution Engine** banaya hai. Yahan workflows hard-coded code nahi hain, balki Excel se dynamically load hone wali configurations hain. Natural language request ko agent samajhta hai, sahi workflow route karta hai, aur Python ke deterministic tools se execute karta hai."*

---

### 🔹 Part 2: Dynamic Excel Ingestion & Realistic Data (1:15 - 2:15)

🖥️ **Screen Par Kya Dikhana Hai:**  
Streamlit UI par **Tab 2: "Excel Workflow Registry"** click karo, ya VS Code me `data/` folder dikhao.

🗣️ **Aapko Kya Bolna Hai (Narration):**
> *"Ab baat karte hain data aur workflows ki.*
>
> *`src/loader.py` me `ExcelWorkflowLoader` use karke hum original Excel sheet `AI_Agent_Workflow_Assessment (1).xlsx` ko runtime par read karte hain. Workflows ke steps, triggers, decision logic, aur tools Excel se aate hain.*
>
> *Kyunki company ki Excel sheet me sirf workflows ki definitions thi aur actual business records nahi the, isliye maine demonstration aur realistic testing ke liye `data/` folder me synthetic datasets create kiye hain — jaise product inventory, vendor prices, customer orders with FedEx tracking, aur employee directory."*

---

### 🔹 Part 3: Dual-Mode LLM & Mock Intent Engine (2:15 - 3:00)

🖥️ **Screen Par Kya Dikhana Hai:**  
VS Code me `src/llm/factory.py` ya `src/llm/mock_provider.py` open karo.

🗣️ **Aapko Kya Bolna Hai (Narration):**
> *"Ab aate hain LLM aur Model architecture par — yeh humare project ka ek bahut important design decision hai.*
>
> *Humne yahan **Dual-Mode LLM Architecture (Factory Pattern)** use kiya hai:*
> 1. *Production me live AI routing ke liye **OpenAI GPT-4o-mini** integrated hai.*
> 2. *Lekin evaluation aur local testing ke liye maine ek **Deterministic Intent Engine (Mock LLM Provider)** banaya hai.*
>
> *Iska sabse bada benefit yeh hai ki jab evaluator ya reviewer is project ko clone karega, toh unhe apna credit card ya paid OpenAI API key daalne ki zaroorat nahi hai. Yeh bina kisi API key ke bhi zero cost par 100% testable hai aur 0.001 second me instant response deta hai. Aur jaise hi aap `.env` me OpenAI key doge, yeh automatically live OpenAI model par switch ho jata hai."*

---

### 🔹 Part 4: Live Execution Demo in Streamlit (3:00 - 4:45)

🖥️ **Screen Par Kya Dikhana Hai:**  
Browser me **Streamlit UI** kholo aur **Tab 1: "Workflow Agent Runner"** par jao.

#### 📍 Demo A: WF001 (Inventory Restock)
1. Dropdown se select karo: `[WF001] Which products need restocking?`
2. Click **"Execute Workflow"** button.
3. **Screen par point karo:**
   - Selected Workflow: `WF001 - Inventory Restock Check (Confidence: 96%)`
   - Ordered Steps: 5 steps executed with green ticks.
   - Tools Invoked: `csv_reader`, `calculator`, `check_inventory_restock`.
   - Condition Box: Check stock threshold rule evaluated.
   - Final Table: Target Capacity aur Suggested Reorder units.

🗣️ **Aapko Kya Bolna Hai:**
> *"Ab live demo dekhte hain. Pehla test query select karte hain: **'Which products need restocking?'**.*
> *Agent ne intent pehchana ki yeh `WF001` hai. Isne 5 steps execute kiye, inventory read ki, calculator tool se calculation kiya.*
> *Yahan table me dekhiye — humne **Target Capacity** aur formula `(Target - Current Stock)` clearly display kiya hai taaki inventory buffer maintain rahe."*

#### 📍 Demo B: WF002 (Product Price Validation)
1. Dropdown se select karo: `[WF002] Find products where vendor price differs by more than 10%.`
2. Click **"Execute Workflow"**.
3. **Screen par point karo:**
   - Condition box: `Price Difference Tolerance Check (Flag when diff > 10%)`.
   - Table me `FLAGGED (>10%)` vs `WITHIN_TOLERANCE`.

🗣️ **Aapko Kya Bolna Hai:**
> *"Ab second workflow: **Price Validation**. Query: **'Find products where vendor price differs by more than 10%'**.*
> *Yahan decision logic pure Python me run hoti hai. Agar difference 10% se zyada hai toh status **FLAGGED** aata hai jaise SKU-101 (20% diff). Aur agar 10% ke andar hai toh **WITHIN_TOLERANCE** aata hai."*

#### 📍 Demo C: WF005 (Customer Order Status)
1. Dropdown se select karo: `[WF005] Where is order ORD-1001?`
2. Click **"Execute Workflow"**.
3. **Screen par point karo:**
   - Order found: Shipped, carrier FedEx, tracking number `TRK-9876543210`.

🗣️ **Aapko Kya Bolna Hai:**
> *"Third demo: **WF005 Order Tracking**. Query: **'Where is order ORD-1001?'**.*
> *Agent ne dynamically identifier `ORD-1001` extract kiya, database query kiya, aur real-time carrier tracking details return ki. Aur agar order exist nahi karta, toh decision logic user se sahi order ID maangti hai bina crash huye."*

---

### 🔹 Part 5: Demonstrating 11th Workflow Extensibility (4:45 - 5:45)

🖥️ **Screen Par Kya Dikhana Hai:**  
Streamlit UI me **Tab 3: "11th Workflow Extensibility"** click karo.

1. Screen par dikhao code explanation: *"Adding an 11th workflow requires only registering the definition row and a tool"*.
2. Click the button: **"Register & Execute WF011 (Live Extensibility Test)"**.
3. Screen par instant green success box aayega: `WF011: Customer Churn Risk Alert` with 5 steps and risk report table.

🗣️ **Aapko Kya Bolna Hai (Very Important!):**
> *"Assignment ka sabse crucial evaluation criteria yeh hai ki **kya humara architecture 11th workflow ko easily support karta hai?**.*
>
> *Tab 3 me hum live test karte hain: Humne ek naya workflow define kiya — **WF011: Customer Churn Risk Alert**.*
> *Iske liye hume purane 10 workflows ke code me ek line bhi change nahi karni padi! Humne sirf:*
> 1. *Ek row registry me add ki (jaise Excel me nayi row judti hai).*
> 2. *Ek tool function `@tool_registry.register` se register kiya.*
>
> *Jaise hi maine button click kiya, agent ne dynamically WF011 ko identify kiya, 5 steps execute kiye, churn decision check kiya, aur high-risk accounts ki table generate kar di — jabki purane 10 workflows bilkul seamlessly chalte rahe."*

---

### 🔹 Part 6: Automated Test Suite & Conclusion (5:45 - 6:30)

🖥️ **Screen Par Kya Dikhana Hai:**  
Terminal / VS Code Terminal kholo.

1. Command run karo:
   ```bash
   python -m pytest -v
   ```
   *(Screen par 20 passed green dikhega).*
2. Command run karo:
   ```bash
   python cli.py --benchmark
   ```
   *(Screen par 10/10 workflows passed dikhega).*

🗣️ **Aapko Kya Bolna Hai:**
> *"System ki reliability prove karne ke liye maine automated test suite banaya hai.*
>
> *Jaisa ki aap terminal me dekh sakte hain:*
> - *`python -m pytest -v` run karne par **20 ke 20 automated tests pass** ho rahe hain — jisme Excel integrity, all 10 workflows, boundary conditions, edge cases, aur 11th workflow extension test shamil hain.*
> - *Aur `python cli.py --benchmark` run karne par workbook ke **10/10 evaluation questions 100% success** ke sath pass hote hain.*
>
> *Poora source code, datasets, setup instructions, aur architecture documentation GitHub repository par available hai. Thank you so much for your time!"*

---

## 🎯 Quick Recording Tips for Harjeet:
1. **Pacing:** Hadhbadi me mat bolna, shaant aur confident awaz me bolna.
2. **Visual Pause:** Jab bhi koi button dabao (jaise WF001 ya WF011), 2 second wait karna taaki viewer screen par table aur steps ko aaram se dekh sake.
3. **Finish:** Loom recording stop karke link copy karein aur GitHub repo ke sath submit kar dein!
