"""Read-only, deterministic tools over the ResQ-AI demo command-center state."""
from __future__ import annotations

import os
from typing import Any


def _active(incident: dict[str, Any]) -> bool:
    return str(incident.get("status", "")).lower() != "resolved"


def list_incidents(center: Any, status: str = "active", limit: int = 10) -> dict[str, Any]:
    """List incidents ordered by the existing deterministic priority score."""
    normalized = (status or "active").strip().lower()
    rows = list(center.incidents)
    if normalized not in {"all", "*"}:
        if normalized in {"active", "open", "unresolved"}:
            rows = [row for row in rows if _active(row)]
        else:
            rows = [row for row in rows if str(row.get("status", "")).lower() == normalized]
    rows.sort(key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    safe_limit = max(1, min(int(limit), 50))
    return {
        "data_mode": "simulated_demo_data" if getattr(center, "demo_mode", True) else "application_state",
        "count": len(rows),
        "incidents": [public_incident(center, row) for row in rows[:safe_limit]],
        "note": "Priority scores are calculated by ResQ-AI's deterministic engine; this tool does not authorize dispatch.",
    }


def public_incident(center: Any, incident: dict[str, Any]) -> dict[str, Any]:
    assignment = center.assignment_for(str(incident.get("id", ""))) if hasattr(center, "assignment_for") else None
    return {
        "id": incident.get("id"),
        "disaster_type": incident.get("disaster_type"),
        "urgency": incident.get("urgency"),
        "priority_score": int(incident.get("priority_score") or 0),
        "status": incident.get("status"),
        "people_affected": int(incident.get("people_affected") or 0),
        "medical_emergency": incident.get("medical_emergency", False),
        "vulnerable_population": int(incident.get("vulnerable_population") or 0),
        "accessibility": incident.get("accessibility"),
        "summary": incident.get("summary") or incident.get("description") or "",
        "recommended_action": incident.get("recommended_action") or "",
        "assignment_recommendation": {
            "resource_id": (assignment or {}).get("resource_id"),
            "resource_name": (assignment or {}).get("resource_name"),
            "hospital_name": (assignment or {}).get("hospital_name"),
            "shelter_name": (assignment or {}).get("shelter_name"),
            "reason": (assignment or {}).get("reason"),
        } if assignment else None,
    }


def get_incident_details(center: Any, incident_id: str) -> dict[str, Any]:
    """Return one incident and its explainable priority breakdown."""
    target = str(incident_id or "").strip().upper()
    incident = next((row for row in center.incidents if str(row.get("id", "")).upper() == target), None)
    if not incident:
        return {"found": False, "incident_id": target, "message": "No matching incident was found in the current ResQ-AI data."}
    result = public_incident(center, incident)
    result["priority_breakdown"] = incident.get("priority_breakdown", [])
    result["formula_note"] = incident.get("formula_note", "")
    result["description"] = incident.get("description", "")
    return {"found": True, "incident": result, "data_mode": "simulated_demo_data" if getattr(center, "demo_mode", True) else "application_state"}


def explain_priority(center: Any, incident_id: str) -> dict[str, Any]:
    """Explain the score computed by the existing deterministic priority engine."""
    result = get_incident_details(center, incident_id)
    if not result.get("found"):
        return result
    incident = result["incident"]
    return {
        "incident_id": incident["id"],
        "priority_score": incident["priority_score"],
        "urgency": incident["urgency"],
        "breakdown": incident["priority_breakdown"],
        "formula_note": incident["formula_note"],
        "explanation": "This explanation reports the existing deterministic score; the language model does not change the score.",
    }


def get_resource_status(center: Any) -> dict[str, Any]:
    """Summarize rescue-team availability and hospital capacity."""
    resources = [{
        "id": row.get("id"), "name": row.get("name"), "type": row.get("type"),
        "status": row.get("status"), "medical_capable": row.get("medical_capable", False),
    } for row in center.resources]
    hospitals = [{
        "id": row.get("id"), "name": row.get("name"),
        "available_beds": int(row.get("available_beds") or 0),
        "total_beds": int(row.get("total_beds") or 0),
    } for row in center.hospitals]
    shelters = [{
        "id": row.get("id"), "name": row.get("name"),
        "capacity": int(row.get("capacity") or 0), "occupied": int(row.get("occupied") or 0),
        "spaces_available": max(0, int(row.get("capacity") or 0) - int(row.get("occupied") or 0)),
    } for row in center.shelters]
    return {
        "resources": resources,
        "available_resource_count": sum(str(row.get("status", "")).lower() == "available" for row in center.resources),
        "hospital_beds_available": sum(row["available_beds"] for row in hospitals),
        "hospitals": hospitals,
        "shelter_spaces_available": sum(row["spaces_available"] for row in shelters),
        "shelters": shelters,
        "data_mode": "simulated_demo_data" if getattr(center, "demo_mode", True) else "application_state",
    }


def find_shelters(center: Any, minimum_spaces: int = 0) -> dict[str, Any]:
    """Find shelters with at least the requested number of unoccupied spaces."""
    minimum = max(0, int(minimum_spaces))
    rows = []
    for shelter in center.shelters:
        capacity = int(shelter.get("capacity") or 0)
        occupied = int(shelter.get("occupied") or 0)
        spaces = max(0, capacity - occupied)
        if spaces >= minimum:
            rows.append({
                "id": shelter.get("id"), "name": shelter.get("name"),
                "address": shelter.get("address"), "capacity": capacity,
                "occupied": occupied, "spaces_available": spaces,
            })
    rows.sort(key=lambda row: row["spaces_available"], reverse=True)
    return {"minimum_spaces": minimum, "count": len(rows), "shelters": rows,
            "note": "Capacity comes from simulated prototype data; verify availability with local authorities."}


def _deterministic_brief(center: Any) -> str:
    metrics = center.metrics()
    simulated = getattr(center, "demo_mode", True)
    incidents = sorted((row for row in center.incidents if _active(row)), key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    lines = [
        "RESQ-AI RESPONSE BRIEF (deterministic fallback)",
        f"Data source: {'simulated demo data' if simulated else 'current application session data'}.",
        f"Active incidents: {metrics.get('active_incidents', 0)}; critical incidents: {metrics.get('critical_incidents', 0)}.",
        f"People affected: {metrics.get('people_affected', 0)}; available resources: {metrics.get('available_resources', 0)}.",
        f"Hospital beds reported available: {metrics.get('hospital_beds_available', 0)}; shelter spaces reported available: {metrics.get('shelter_spaces_available', 0)}.",
    ]
    for row in incidents[:3]:
        lines.append(f"- {row.get('id')}: {row.get('disaster_type')} | score {row.get('priority_score', 0)}/100 | {row.get('people_affected', 0)} people affected | {row.get('recommended_action', 'Review with coordinator')}")
    lines.append("Coordinator action: verify reports and capacities, then make all operational decisions. Scores and allocations are recommendations, not dispatch authorization.")
    return "\n".join(lines)


def generate_incident_brief(
    center: Any,
    model_id: str | None = None,
    region: str | None = None,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_session_token: str | None = None,
) -> dict[str, Any]:
    """Create a briefing from the supplied app state, optionally using Bedrock."""
    model_id = (model_id or os.getenv("AWS_BEDROCK_MODEL_ID", "")).strip()
    region = (region or os.getenv("AWS_REGION", "us-east-1")).strip()
    if not model_id:
        return {"mode": "deterministic_fallback", "brief": _deterministic_brief(center),
                "aws_note": "Add AWS_BEDROCK_MODEL_ID and AWS_REGION to Streamlit secrets, then configure AWS credentials to enable Amazon Bedrock."}
    try:
        import boto3
        simulated = getattr(center, "demo_mode", True)
        source_note = "simulated demo data" if simulated else "the current application session data"
        credentials = {}
        if aws_access_key_id and aws_secret_access_key:
            credentials = {
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
            }
            if aws_session_token:
                credentials["aws_session_token"] = aws_session_token
        response = boto3.client("bedrock-runtime", region_name=region, **credentials).converse(
            modelId=model_id,
            system=[{"text": f"You are a disaster-response briefing assistant. Use only supplied {source_note}. Do not invent facts, claim live feeds, or authorize dispatch. Clearly state uncertainty and that a human coordinator must decide. Deterministic priority scores in the input must not be changed."}],
            messages=[{"role": "user", "content": [{"text": _deterministic_brief(center)}]}],
            inferenceConfig={"maxTokens": 500, "temperature": 0.1},
        )
        content = response.get("output", {}).get("message", {}).get("content", [])
        brief = "\n".join(str(item.get("text", "")) for item in content if item.get("text"))
        if not brief.strip():
            raise RuntimeError("Empty Bedrock response")
        return {"mode": "amazon_bedrock", "model_id": model_id, "region": region, "brief": brief,
                "note": f"AI-generated briefing based only on {source_note}; coordinator review required."}
    except Exception:
        return {"mode": "deterministic_fallback", "brief": _deterministic_brief(center),
                "aws_note": "Amazon Bedrock was configured but unavailable. Returned a deterministic briefing instead."}
