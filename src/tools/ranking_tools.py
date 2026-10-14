import os
import json
from typing import Dict, Any, List, Optional
from src.tools.registry import tool_registry


@tool_registry.register("assign_employee_task", "Ranks team candidates based on skills & capacity and assigns task (WF009)")
def assign_employee_task(
    task_description: str = "Urgent task assignment",
    required_skills: Optional[List[str]] = None,
    priority: str = "Medium",
    deadline: str = "2026-10-20",
    employees_file: str = "data/employees.json"
) -> Dict[str, Any]:
    """
    Executes WF009: Employee Task Assignment
    - Matches required skills against employee directory
    - Computes workload capacity (100% - current_workload_pct)
    - Decision Logic:
      * Prefer employees with required skills and available capacity
      * Escalate if no suitable employee exists (or if all qualified employees are at 100% workload)
    """
    if not os.path.exists(employees_file):
        raise FileNotFoundError(f"Employee database not found: {employees_file}")

    with open(employees_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    employees = data.get("employees", [])
    skills_needed = [s.strip().lower() for s in (required_skills or ["Python"])]

    # Candidate evaluation
    ranked_candidates = []

    for emp in employees:
        emp_skills = [s.lower() for s in emp.get("skills", [])]
        matched_skills = [s for s in skills_needed if s in emp_skills]

        # Must have at least one required skill to qualify
        if not matched_skills:
            continue

        workload = emp.get("current_workload_pct", 50)
        available_capacity = max(0, 100 - workload)

        # Ranking score: skill match weight + available capacity
        score = (len(matched_skills) * 25) + available_capacity

        ranked_candidates.append({
            "employee_id": emp.get("employee_id"),
            "name": emp.get("name"),
            "role": emp.get("role"),
            "matched_skills": matched_skills,
            "all_skills": emp.get("skills"),
            "current_workload_pct": workload,
            "available_capacity_pct": available_capacity,
            "ranking_score": score,
            "is_fully_booked": workload >= 100
        })

    # Decision Logic: Check if escalation is required
    # Escalate if: No candidates matched skills OR all matched candidates are at 100% workload
    available_candidates = [c for c in ranked_candidates if not c["is_fully_booked"]]

    if not ranked_candidates:
        return {
            "status": "ESCALATED",
            "decision": "ESCALATE_TO_MANAGER",
            "reason": f"No employee in the directory possesses the required skills: {required_skills or ['Python']}.",
            "task_details": {
                "description": task_description,
                "required_skills": required_skills or ["Python"],
                "priority": priority,
                "deadline": deadline
            },
            "candidates_evaluated_count": len(employees)
        }

    if not available_candidates:
        return {
            "status": "ESCALATED",
            "decision": "ESCALATE_TO_MANAGER",
            "reason": f"All qualified employees possessing the required skills are currently at 100% workload capacity.",
            "task_details": {
                "description": task_description,
                "required_skills": required_skills or ["Python"],
                "priority": priority,
                "deadline": deadline
            },
            "overbooked_qualified_candidates": ranked_candidates
        }

    # Sort available candidates by score descending
    available_candidates.sort(key=lambda x: x["ranking_score"], reverse=True)
    best_candidate = available_candidates[0]

    return {
        "status": "SUCCESS",
        "decision": "ASSIGNED",
        "assigned_employee": {
            "employee_id": best_candidate["employee_id"],
            "name": best_candidate["name"],
            "role": best_candidate["role"],
            "skills_matched": best_candidate["matched_skills"],
            "current_workload_pct": f"{best_candidate['current_workload_pct']}%",
            "available_capacity_pct": f"{best_candidate['available_capacity_pct']}%",
            "fit_score": best_candidate["ranking_score"]
        },
        "assignment_rationale": (
            f"Selected {best_candidate['name']} ({best_candidate['role']}) due to strong skill match "
            f"({', '.join(best_candidate['matched_skills'])}) and highest available capacity "
            f"({best_candidate['available_capacity_pct']}% free)."
        ),
        "task_manifest": {
            "task_description": task_description,
            "priority": priority,
            "deadline": deadline,
            "status": "Assigned & In Progress"
        },
        "all_ranked_candidates": available_candidates
    }
