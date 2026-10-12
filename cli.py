import sys
import argparse
from src.loader import workflow_loader
from src.engine import workflow_engine


def print_banner():
    print("=" * 80)
    print("  AI AGENT WORKFLOW AUTOMATION SYSTEM")
    print("  Enterprise Reusable Architecture - Excel Driven")
    print("=" * 80)


def print_execution_result(res):
    print("\n" + "-" * 80)
    print(f"User Request:          \"{res.user_request}\"")
    print(f"Selected Workflow:     {res.selected_workflow_id or 'None'} - {res.selected_workflow_name or 'N/A'}")
    print(f"Routing Confidence:    {round(res.selection_confidence * 100, 1)}%")
    print(f"Routing Rationale:     {res.selection_reasoning}")
    print(f"Execution Status:      {res.status}")
    print(f"Total Duration:        {res.duration_seconds}s")
    print("-" * 80)

    print("\nOrdered Steps Executed:")
    if res.steps_executed:
        for s in res.steps_executed:
            badge = "[OK]" if s.status == "SUCCESS" else f"[{s.status}]"
            tool_info = f" (Tool: {s.tool_name})" if s.tool_name else ""
            print(f"  {s.step_number}. {badge} {s.step_name}{tool_info}")
            if s.tool_output_summary:
                print(f"     -> {s.tool_output_summary}")
    else:
        print("  (No steps executed)")

    print("\nConditions & Decisions Evaluated:")
    if res.conditions_evaluated:
        for c in res.conditions_evaluated:
            flag = "[TRUE]" if c.outcome else "[FALSE]"
            print(f"  * {flag} {c.condition_name}")
            print(f"    Rule: {c.rule_expression}")
            print(f"    Outcome: {c.explanation}")
    else:
        print("  (No conditions evaluated)")

    print("\nTools Invoked:")
    print(f"  {', '.join(res.tools_invoked) if res.tools_invoked else 'None'}")

    print("\nFinal Business Output:")
    print(res.final_summary)
    print("=" * 80 + "\n")


def run_benchmark():
    """Runs all 10 test questions from the Excel workbook sequentially."""
    print("\n>>> Running Automated Evaluation on 10 Workbook Test Questions <<<\n")
    questions = workflow_loader.get_test_questions()
    
    passed_count = 0
    for idx, q in enumerate(questions, start=1):
        print(f"\n[{idx}/10] Testing: \"{q.test_request}\" (Expected: {q.workflow_id})")
        res = workflow_engine.execute_request(q.test_request)
        is_match = res.selected_workflow_id == q.workflow_id
        if is_match and res.status == "SUCCESS":
            passed_count += 1
            print(f"  -> SUCCESS! Matched {res.selected_workflow_id} ({res.selected_workflow_name}) in {res.duration_seconds}s")
            print(f"     Steps executed: {len(res.steps_executed)} | Tools: {res.tools_invoked}")
        else:
            print(f"  -> ISSUE: Expected {q.workflow_id}, Got {res.selected_workflow_id}, Status: {res.status}")

    print(f"\nBenchmark Summary: {passed_count}/{len(questions)} workflows passed evaluation successfully.")


def main():
    parser = argparse.ArgumentParser(description="AI Agent Workflow Automation System CLI")
    parser.add_argument("--benchmark", action="store_true", help="Run all 10 workbook test questions")
    parser.add_argument("--query", type=str, help="Execute a single natural language query")

    args = parser.parse_args()
    print_banner()

    if args.benchmark:
        run_benchmark()
        return

    if args.query:
        res = workflow_engine.execute_request(args.query)
        print_execution_result(res)
        return

    # Interactive mode
    print("Enter a natural language request, or type 'test' to run benchmark, or 'exit' to quit.\n")
    while True:
        try:
            user_input = input("Agent Prompt > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting system. Goodbye!")
                break
            if user_input.lower() in ["test", "benchmark"]:
                run_benchmark()
                continue

            res = workflow_engine.execute_request(user_input)
            print_execution_result(res)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting system.")
            break


if __name__ == "__main__":
    main()
