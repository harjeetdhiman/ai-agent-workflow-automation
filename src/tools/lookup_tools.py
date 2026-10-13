import os
import json
from typing import Dict, Any
from src.tools.registry import tool_registry


@tool_registry.register("lookup_order_status", "Searches order database and shipment tracking by order ID or email (WF005)")
def lookup_order_status(
    identifier: str,
    orders_file: str = "data/orders_database.json"
) -> Dict[str, Any]:
    """
    Executes WF005: Customer Order Status
    - Validates order identifier (Order ID or customer email)
    - Decision Logic: If no order is found, prompt for a valid identifier
    - Returns order status, item details, shipment carrier, and real-time tracking
    """
    if not os.path.exists(orders_file):
        raise FileNotFoundError(f"Orders database file not found: {orders_file}")

    with open(orders_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    orders = data.get("orders", [])
    clean_id = identifier.strip().lower()

    found_order = None
    for order in orders:
        if (
            order.get("order_id", "").strip().lower() == clean_id
            or order.get("customer_email", "").strip().lower() == clean_id
        ):
            found_order = order
            break

    # Decision Logic: If no order is found, ask for another identifier
    if not found_order:
        return {
            "found": False,
            "searched_identifier": identifier,
            "message": f"No order found matching identifier '{identifier}'. Please provide a valid Order ID (e.g. ORD-1001) or customer email.",
            "status": "NOT_FOUND"
        }

    shipment = found_order.get("shipment")
    has_shipment = shipment is not None

    return {
        "found": True,
        "order_id": found_order.get("order_id"),
        "customer_name": found_order.get("customer_name"),
        "customer_email": found_order.get("customer_email"),
        "order_date": found_order.get("order_date"),
        "order_status": found_order.get("status"),
        "total_amount": found_order.get("total_amount"),
        "items": found_order.get("items", []),
        "has_tracking": has_shipment,
        "shipment_details": {
            "carrier": shipment.get("carrier") if has_shipment else "Not yet assigned",
            "tracking_number": shipment.get("tracking_number") if has_shipment else "Pending dispatch",
            "tracking_status": shipment.get("status") if has_shipment else "Awaiting warehouse fulfillment",
            "current_location": shipment.get("current_location") if has_shipment else "Warehouse",
            "estimated_delivery": shipment.get("estimated_delivery") if has_shipment else "TBD",
            "last_updated": shipment.get("last_updated") if has_shipment else "N/A"
        } if has_shipment else None,
        "status": "RETRIEVED"
    }


@tool_registry.register("lookup_employee_roster", "Queries employee profiles, skills, and current workload capacity (WF009)")
def lookup_employee_roster(
    employees_file: str = "data/employees.json"
) -> Dict[str, Any]:
    """Retrieves full employee directory for skill matching and task assignment."""
    if not os.path.exists(employees_file):
        raise FileNotFoundError(f"Employee database not found: {employees_file}")

    with open(employees_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data
