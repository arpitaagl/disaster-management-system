"""In-memory command-center state: score, assign, log, mutate, recalculate."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from core.ai_engine import analyze_incident
from core.config import CITY_LAT, CITY_LON
from core.database import load_demo_bundle  # Explicit fixture used only by labelled export tests.
from core.geo import nearest
from core.optimizer import assign_resources
from core.priority import calculate_priority, recommended_action
from utils.logging import make_event
from utils.validation import as_int


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _next_id(rows: list[dict[str, Any]], prefix: str) -> str:
    nums = []
    for row in rows:
        text = str(row.get("id") or "")
        if text.startswith(prefix):
            tail = text[len(prefix) :].lstrip("-")
            try:
                nums.append(int(tail))
            except ValueError:
                continue
    return f"{prefix}-{max(nums, default=0) + 1:03d}"


class CommandCenter:
    def __init__(self, bundle: dict[str, list[dict[str, Any]]] | None = None) -> None:
        data = bundle if bundle is not None else {"incidents": [], "resources": [], "hospitals": [], "shelters": [], "roads": [], "events": []}
        self.incidents: list[dict[str, Any]] = data.get("incidents", [])
        self.resources: list[dict[str, Any]] = data.get("resources", [])
        self.hospitals: list[dict[str, Any]] = data.get("hospitals", [])
        self.shelters: list[dict[str, Any]] = data.get("shelters", [])
        self.roads: list[dict[str, Any]] = data.get("roads", [])
        self.events: list[dict[str, Any]] = data.get("events", [])
        self.assignments: list[dict[str, Any]] = []
        self.demo_mode = False
        self.ai_mode = "Fallback Analysis Mode"
        if not self.events:
            self.events.append(make_event("Command center initialized; awaiting incident reports and verified operational feeds", "system"))
        self.recalculate(reason="Command center initialized with no verified operational records")

    def log(self, message: str, category: str = "info") -> None:
        self.events.insert(0, make_event(message, category))
        self.events = self.events[:200]

    def to_dict(self) -> dict[str, Any]:
        return {
            "incidents": deepcopy(self.incidents),
            "resources": deepcopy(self.resources),
            "hospitals": deepcopy(self.hospitals),
            "shelters": deepcopy(self.shelters),
            "roads": deepcopy(self.roads),
            "events": deepcopy(self.events),
            "assignments": deepcopy(self.assignments),
            "demo_mode": self.demo_mode,
            "ai_mode": self.ai_mode,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CommandCenter":
        cc = cls.__new__(cls)
        cc.incidents = payload.get("incidents", [])
        cc.resources = payload.get("resources", [])
        cc.hospitals = payload.get("hospitals", [])
        cc.shelters = payload.get("shelters", [])
        cc.roads = payload.get("roads", [])
        cc.events = payload.get("events", [])
        cc.assignments = payload.get("assignments", [])
        cc.demo_mode = payload.get("demo_mode", False)
        cc.ai_mode = payload.get("ai_mode", "Fallback Analysis Mode")
        return cc

    def assignment_for(self, incident_id: str) -> dict[str, Any] | None:
        for row in self.assignments:
            if row.get("incident_id") == incident_id:
                return row
        return None

    def recalculate(self, reason: str = "Recalculated response plan") -> None:
        for incident in self.incidents:
            _, dist, _ = nearest(
                float(incident.get("lat") or CITY_LAT),
                float(incident.get("lon") or CITY_LON),
                [r for r in self.resources if str(r.get("status")).lower() == "available"],
                roads=self.roads,
            )
            result = calculate_priority(incident, nearest_resource_km=None if dist == float("inf") else dist)
            incident["priority_score"] = result["score"]
            incident["urgency"] = result["urgency"]
            incident["priority_breakdown"] = result["components"]
            incident["formula_note"] = result["formula_note"]
            incident["recommended_action"] = recommended_action(incident, result["urgency"])

        self.assignments = assign_resources(
            self.incidents,
            self.resources,
            self.roads,
            self.hospitals,
            self.shelters,
        )
        assigned_ids = {a["incident_id"] for a in self.assignments if a.get("resource_id")}
        for incident in self.incidents:
            if str(incident.get("status")).lower() == "resolved":
                continue
            incident["status"] = "Assigned" if incident.get("id") in assigned_ids else "Active"
        self.log(reason, "plan")

    def analyze_and_add_incident(
        self,
        description: str,
        people_affected: int,
        lat: float,
        lon: float,
        accessibility: str = "Open",
        reporter: str = "",
        image_name: str = "",
        location_text: str = "",
    ) -> dict[str, Any]:
        analysis = analyze_incident(description, people_affected, accessibility)
        self.ai_mode = analysis.get("ai_mode", "Fallback Analysis Mode")
        incident_id = _next_id(self.incidents, "INC")
        people = analysis.get("people_affected") or people_affected
        incident = {
            "id": incident_id,
            "disaster_type": analysis["disaster_type"],
            "description": description.strip(),
            "summary": analysis.get("summary") or description.strip()[:180],
            "severity": analysis["severity"],
            "people_affected": people,
            "medical_emergency": analysis["medical_emergency"],
            "vulnerable_population": analysis.get("vulnerable_population") or 0,
            "accessibility": analysis["accessibility"] or accessibility,
            "status": "Active",
            "lat": float(lat),
            "lon": float(lon),
            "location_text": str(location_text or "").strip(),
            "reported_at": _now_iso(),
            "reporter": reporter or "anonymous",
            "image_name": image_name,
            "source": "operator-report",
        }
        self.incidents.append(incident)
        self.log(f"New {incident['disaster_type']} incident {incident_id} received", "incident")
        engine = "AI classification" if analysis.get("engine") == "llm" else "Fallback classification"
        self.log(f"{engine} completed for {incident_id}: {incident['disaster_type']}", "ai")
        self.recalculate(reason=f"Priority and allocation recalculated after {incident_id}")
        self.log(
            f"Priority calculated: {incident.get('priority_score')} for {incident_id}",
            "priority",
        )
        assign = self.assignment_for(incident_id)
        if assign and assign.get("resource_id"):
            self.log(f"Resource {assign['resource_id']} recommended for {incident_id}", "assign")
        return {"incident": incident, "analysis": analysis, "assignment": assign}

    def set_resource_status(self, resource_id: str, status: str) -> None:
        for resource in self.resources:
            if resource.get("id") == resource_id:
                resource["status"] = status
                self.log(f"Resource {resource_id} marked {status}", "scenario")
                break
        self.recalculate(reason="Resource allocation recalculated")

    def set_road_status(self, road_id: str, status: str) -> None:
        for road in self.roads:
            if road.get("id") == road_id:
                road["status"] = status
                self.log(f"Road {road_id} marked {status}", "scenario")
                break
        self.recalculate(reason="Routing constraints updated; plan recalculated")

    def set_hospital_beds(self, hospital_id: str, available_beds: int) -> None:
        for hospital in self.hospitals:
            if hospital.get("id") == hospital_id:
                hospital["available_beds"] = max(0, int(available_beds))
                self.log(f"Hospital {hospital_id} available beds set to {hospital['available_beds']}", "scenario")
                break
        self.recalculate(reason="Hospital capacity updated; plan recalculated")

    def set_shelter_occupied(self, shelter_id: str, occupied: int) -> None:
        for shelter in self.shelters:
            if shelter.get("id") == shelter_id:
                cap = as_int(shelter.get("capacity"), 0)
                shelter["occupied"] = max(0, min(cap, int(occupied)))
                self.log(f"Shelter {shelter_id} occupancy set to {shelter['occupied']}", "scenario")
                break
        self.recalculate(reason="Shelter capacity updated; plan recalculated")

    def bump_people(self, incident_id: str, people: int) -> None:
        for incident in self.incidents:
            if incident.get("id") == incident_id:
                incident["people_affected"] = max(0, int(people))
                self.log(f"{incident_id} people affected updated to {people}", "scenario")
                break
        self.recalculate(reason="Impact estimate updated; priorities recalculated")

    def metrics(self) -> dict[str, int]:
        active = [i for i in self.incidents if str(i.get("status")).lower() != "resolved"]
        critical = [i for i in active if str(i.get("urgency")).lower() == "critical" or as_int(i.get("priority_score")) >= 85]
        medical = [i for i in active if i.get("medical_emergency") in (True, "True", "true", "yes", 1, "1")]
        people = sum(as_int(i.get("people_affected")) for i in active)
        available = [r for r in self.resources if str(r.get("status")).lower() == "available"]
        assigned = [a for a in self.assignments if a.get("resource_id")]
        attention = [i for i in active if as_int(i.get("priority_score")) >= 80]
        hosp_avail = sum(as_int(h.get("available_beds")) for h in self.hospitals)
        hosp_total = sum(as_int(h.get("total_beds")) for h in self.hospitals)
        shel_avail = sum(as_int(s.get("capacity")) - as_int(s.get("occupied")) for s in self.shelters)
        return {
            "active_incidents": len(active),
            "critical_incidents": len(critical),
            "people_affected": people,
            "available_resources": len(available),
            "assigned_resources": len(assigned),
            "medical_emergencies": len(medical),
            "needs_attention": len(attention),
            "hospital_beds_available": hosp_avail,
            "hospital_beds_total": hosp_total,
            "shelter_spaces_available": shel_avail,
        }


def load_demo_disaster() -> CommandCenter:
    cc = CommandCenter(load_demo_bundle())
    cc.demo_mode = True
    # Prepared flood-city scenario: limited teams, one blocked arterial, tight hospital capacity.
    cc.set_road_status("R-07", "Blocked")
    for resource in cc.resources:
        if resource.get("id") in {"R08", "R10"}:
            resource["status"] = "Unavailable"
    for hospital in cc.hospitals:
        if hospital.get("id") == "H01":
            hospital["available_beds"] = 4
        if hospital.get("id") == "H02":
            hospital["available_beds"] = 6
    cc.events = [e for e in cc.events if e.get("category") == "system"][:1]
    cc.log("What-if scenario loaded: flood response constraints applied", "scenario")
    cc.log("Scenario change: Road R-07 marked blocked", "scenario")
    cc.log("Scenario change: Resources R08 and R10 marked unavailable", "scenario")
    cc.recalculate(reason="What-if response plan recalculated")
    return cc
