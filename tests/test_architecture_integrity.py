import ast
import inspect
from pathlib import Path
from src.engine import WorkflowEngine, workflow_engine
from src.loader import WorkflowDefinition, workflow_loader
from src.tools.registry import tool_registry


def test_engine_contains_zero_workflow_id_branches():
    """
    CRITICAL ARCHITECTURE INTEGRITY TEST:
    Enforces that `src/engine.py` contains ZERO hardcoded workflow branches:
    - No comparisons against 'WF001' .. 'WF010'
    - No handler maps or dispatcher dictionaries
    - No `_exec_wfXXX` functions
    - Pure declarative generic orchestration
    """
    engine_file = Path(__file__).resolve().parent.parent / "src" / "engine.py"
    with open(engine_file, "r", encoding="utf-8") as f:
        code = f.read()

    tree = ast.parse(code)

    prohibited_ids = [f"WF{i:03d}" for i in range(1, 12)]

    # 1. Check for hardcoded string comparisons or references to WF001-WF011 in AST
    hardcoded_references = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(node.value.upper() == wf_id for wf_id in prohibited_ids):
                hardcoded_references.append((node.lineno, node.value))

    assert not hardcoded_references, (
        f"Architecture Violation: Found hardcoded workflow ID references in engine.py: {hardcoded_references}. "
        "The engine must be 100% workflow-agnostic."
    )

    # 2. Check for handler dispatch methods
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            assert not node.name.startswith("_exec_wf"), (
                f"Architecture Violation: Found dedicated handler method '{node.name}' in engine.py."
            )

    # 3. Verify that engine delegates tool execution generically
    tool_exec_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and
        isinstance(node.func, ast.Attribute) and
        node.func.attr == "execute"
    ]
    assert len(tool_exec_calls) >= 1, "Engine must invoke tools dynamically via tool_registry.execute()."


def test_generic_execution_of_novel_dynamic_workflow():
    """
    Proves that a completely novel workflow (WF999: Realtime Health Monitor)
    executes its ordered steps and passes context data through the common engine
    without ANY code changes to engine.py.
    """
    # 1. Register novel tool
    @tool_registry.register("health_probe", "Pings microservices and evaluates latency (WF999)")
    def probe_services(target_service: str = "payment-gateway"):
        return {
            "target": target_service,
            "status": "HEALTHY",
            "latency_ms": 28,
            "packet_loss_pct": 0.0
        }

    # 2. Register novel workflow definition
    wf999 = WorkflowDefinition(
        workflow_id="WF999",
        workflow_name="Service Health Diagnostic",
        trigger="User requests microservice latency and uptime health check",
        inputs="Service name, latency threshold",
        steps_raw="Ping service endpoint → measure latency → check degradation threshold → report status",
        steps=[
            "Ping service endpoint",
            "Measure latency",
            "Check degradation threshold",
            "Report status"
        ],
        decision_logic="If latency_ms > 100 or packet_loss_pct > 1%, flag degraded health",
        tools_required=["health_probe", "calculator"],
        expected_output="Health diagnostics report with latency and status"
    )
    workflow_loader._workflows["WF999"] = wf999

    # 3. Execute through generic engine
    result = workflow_engine.execute_request("Check service health and ping latency for payment-gateway")

    assert result.selected_workflow_id == "WF999"
    assert result.status == "SUCCESS"
    assert len(result.steps_executed) == 4
    assert "health_probe" in result.tools_invoked
    assert result.final_result_data is not None
    assert isinstance(result.conditions_evaluated[0].outcome, bool)
    assert "Rule Gate" in result.conditions_evaluated[0].condition_name
