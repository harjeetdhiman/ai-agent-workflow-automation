import os
import csv
from typing import Dict, Any, Optional
from src.tools.registry import tool_registry


@tool_registry.register("check_inventory_restock", "Evaluates inventory against minimum thresholds and computes reorders (WF001)")
def check_inventory_restock(
    file_path: str = "data/inventory.csv",
    min_threshold: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes WF001: Inventory Restock Check
    - Compares current stock with minimum safety threshold
    - Business Rule: If current_stock < minimum_stock, mark product for restock
    - Computes suggested reorder quantity (target_stock - current_stock)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Inventory file not found: {file_path}")

    restock_needed = []
    adequate_stock = []

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sku = row.get("sku", "").strip()
            name = row.get("product_name", "").strip()
            current = int(row.get("current_stock", 0))
            
            # Use SKU's min stock or explicit threshold override
            if min_threshold is not None:
                threshold = int(min_threshold)
            else:
                threshold = int(row.get("minimum_stock", 10))

            target = int(row.get("target_stock", threshold * 2))

            # Condition Logic: current_stock < minimum_stock
            if current < threshold:
                reorder_qty = max(0, target - current)
                restock_needed.append({
                    "sku": sku,
                    "product_name": name,
                    "current_stock": current,
                    "minimum_threshold": threshold,
                    "target_stock": target,
                    "suggested_reorder_qty": reorder_qty,
                    "urgency": "CRITICAL" if current == 0 else "HIGH"
                })
            else:
                adequate_stock.append({
                    "sku": sku,
                    "product_name": name,
                    "current_stock": current,
                    "minimum_threshold": threshold
                })

    return {
        "total_products_checked": len(restock_needed) + len(adequate_stock),
        "products_needing_restock_count": len(restock_needed),
        "products_adequate_count": len(adequate_stock),
        "restock_list": restock_needed,
        "adequate_summary": f"{len(adequate_stock)} products are safely above their minimum thresholds."
    }


@tool_registry.register("validate_product_prices", "Compares internal retail prices with vendor price lists and flags >10% discrepancies (WF002)")
def validate_product_prices(
    internal_file: str = "data/internal_prices.csv",
    vendor_file: str = "data/vendor_prices.csv",
    variance_threshold: float = 0.10
) -> Dict[str, Any]:
    """
    Executes WF002: Product Price Validation
    - Matches internal product catalog with vendor quotes by SKU
    - Business Rule: Flag when price difference exceeds threshold (default 10%)
    - Reports matched items, percentage differences, and anomalies
    """
    if not os.path.exists(internal_file):
        raise FileNotFoundError(f"Internal prices file not found: {internal_file}")
    if not os.path.exists(vendor_file):
        raise FileNotFoundError(f"Vendor prices file not found: {vendor_file}")

    # Load internal prices
    internal_map = {}
    with open(internal_file, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            sku = r.get("sku", "").strip()
            internal_map[sku] = {
                "product_name": r.get("product_name", "").strip(),
                "price": float(r.get("internal_price", 0.0)),
                "currency": r.get("currency", "USD").strip()
            }

    # Load vendor prices
    vendor_items = []
    with open(vendor_file, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            vendor_items.append({
                "sku": r.get("sku", "").strip(),
                "vendor_name": r.get("vendor_name", "").strip(),
                "vendor_price": float(r.get("vendor_price", 0.0)),
                "currency": r.get("currency", "USD").strip()
            })

    matched_results = []
    exceptions = []
    unmatched_vendor_skus = []

    for v in vendor_items:
        sku = v["sku"]
        v_price = v["vendor_price"]
        vendor_name = v["vendor_name"]

        if sku in internal_map:
            int_data = internal_map[sku]
            i_price = int_data["price"]
            diff_abs = round(abs(v_price - i_price), 2)
            diff_pct = round(diff_abs / i_price if i_price > 0 else 0.0, 4)

            # Decision Logic: Flag when diff_pct > variance_threshold (10%)
            is_flagged = diff_pct > variance_threshold

            record = {
                "sku": sku,
                "product_name": int_data["product_name"],
                "internal_price": i_price,
                "vendor_name": vendor_name,
                "vendor_price": v_price,
                "difference_absolute": diff_abs,
                "difference_percentage": round(diff_pct * 100, 2),
                "is_exception": is_flagged,
                "status": "FLAGGED (>10%)" if is_flagged else "WITHIN_TOLERANCE"
            }
            matched_results.append(record)
            if is_flagged:
                exceptions.append(record)
        else:
            unmatched_vendor_skus.append({
                "sku": sku,
                "vendor_name": vendor_name,
                "vendor_price": v_price,
                "note": "SKU exists in vendor feed but not found in internal catalog"
            })

    return {
        "total_vendor_records": len(vendor_items),
        "total_matched": len(matched_results),
        "exceptions_flagged_count": len(exceptions),
        "unmatched_vendor_skus_count": len(unmatched_vendor_skus),
        "variance_threshold_applied": f"{variance_threshold * 100}%",
        "exceptions": exceptions,
        "matched_comparison_summary": matched_results,
        "unmatched_items": unmatched_vendor_skus
    }


@tool_registry.register("aggregate_workflow_performance", "Analyzes workflow logs, success rates, latency, and flags bottlenecks (WF010)")
def aggregate_workflow_performance(
    logs_file: str = "data/execution_logs.csv",
    failure_threshold: float = 0.10,
    latency_threshold: float = 5.0
) -> Dict[str, Any]:
    """
    Executes WF010: Workflow Performance Report
    - Loads execution logs
    - Calculates success/failure rates & average execution time per workflow
    - Decision Logic: Flag workflows with failure rate > 10% OR average duration > threshold
    - Generates actionable optimization recommendations
    """
    if not os.path.exists(logs_file):
        raise FileNotFoundError(f"Execution logs file not found: {logs_file}")

    workflow_stats = {}
    total_runs = 0

    with open(logs_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_runs += 1
            wf_id = row.get("workflow_id", "UNKNOWN").strip()
            wf_name = row.get("workflow_name", "").strip()
            status = row.get("status", "SUCCESS").strip().upper()
            duration = float(row.get("duration_seconds", 0.0))
            err_msg = row.get("error_message", "").strip()
            failed_step = row.get("failed_step", "").strip()

            if wf_id not in workflow_stats:
                workflow_stats[wf_id] = {
                    "workflow_id": wf_id,
                    "workflow_name": wf_name,
                    "runs": 0,
                    "successes": 0,
                    "failures": 0,
                    "durations": [],
                    "errors": [],
                    "failed_steps": []
                }

            st = workflow_stats[wf_id]
            st["runs"] += 1
            st["durations"].append(duration)
            if status == "SUCCESS":
                st["successes"] += 1
            else:
                st["failures"] += 1
                if err_msg:
                    st["errors"].append(err_msg)
                if failed_step:
                    st["failed_steps"].append(failed_step)

    metrics_list = []
    flagged_workflows = []
    recommendations = []

    for wf_id, st in workflow_stats.items():
        runs = st["runs"]
        failures = st["failures"]
        fail_rate = round(failures / runs if runs > 0 else 0.0, 4)
        avg_dur = round(sum(st["durations"]) / len(st["durations"]) if st["durations"] else 0.0, 2)

        # Decision Logic: Flag if fail_rate > 10% OR avg_dur > latency_threshold
        reasons = []
        if fail_rate > failure_threshold:
            reasons.append(f"High failure rate: {round(fail_rate * 100, 1)}% (Threshold: {failure_threshold * 100}%)")
        if avg_dur > latency_threshold:
            reasons.append(f"High latency: {avg_dur}s (Threshold: {latency_threshold}s)")

        metric_record = {
            "workflow_id": wf_id,
            "workflow_name": st["workflow_name"],
            "total_runs": runs,
            "success_count": st["successes"],
            "failure_count": failures,
            "failure_rate_pct": round(fail_rate * 100, 1),
            "avg_duration_sec": avg_dur,
            "is_flagged": len(reasons) > 0,
            "flag_reasons": reasons,
            "top_errors": list(set(st["errors"])),
            "failed_steps": list(set(st["failed_steps"]))
        }
        metrics_list.append(metric_record)

        if reasons:
            flagged_workflows.append(metric_record)
            for r in reasons:
                recommendations.append(f"[{wf_id} - {st['workflow_name']}]: {r}. Investigate steps: {st['failed_steps'] or 'N/A'}")

    # Sort metrics by failure count descending
    metrics_list.sort(key=lambda x: x["failure_count"], reverse=True)

    return {
        "total_executions_analyzed": total_runs,
        "workflows_monitored_count": len(workflow_stats),
        "flagged_workflows_count": len(flagged_workflows),
        "workflow_metrics": metrics_list,
        "flagged_workflows": flagged_workflows,
        "recommendations": recommendations or ["All workflows are performing within established SLA boundaries."]
    }
