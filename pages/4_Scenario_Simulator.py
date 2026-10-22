from __future__ import annotations

import math
import requests
import streamlit as st

from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar

page_setup("Scenario Simulator")

center = get_center()
render_sidebar(center)
render_header(
    center,
    "Assess reported emergencies and review resource readiness using records actually available to ResQ-AI",
)

st.caption(
    "This page uses operator-submitted incidents only. It does not create sample incidents or treat "
    "unverified assets as real. An assessment is not a dispatch confirmation."
)

# This feature reads incidents from the current app session and public service directories.
# It does not require Supabase or an inventory access token.


@st.cache_data(ttl=3600, show_spinner=False)
def _geocode_incident_location(address: str) -> tuple[float, float] | None:
    """Resolve the saved user-entered place name."""
    headers = {"User-Agent": "ResQ-AI disaster response prototype/1.0"}
    try:
        response = requests.get("https://photon.komoot.io/api/", params={"q": address, "limit": 1}, headers=headers, timeout=(3, 8))
        response.raise_for_status()
        features = response.json().get("features") or []
        if features:
            coords = features[0].get("geometry", {}).get("coordinates") or []
            if len(coords) >= 2:
                return float(coords[1]), float(coords[0])
    except (requests.RequestException, ValueError, TypeError, IndexError):
        pass
    try:
        response = requests.get("https://nominatim.openstreetmap.org/search", params={"q": address, "format": "jsonv2", "limit": 1}, headers=headers, timeout=(3, 8))
        response.raise_for_status()
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        pass
    return None


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1.0 - value)))


@st.cache_data(ttl=600, show_spinner=False)
def _nearby_public_services(lat: float, lon: float, radius_m: int = 25000) -> list[dict]:
    """Find public-map-listed facilities through multiple Overpass mirrors."""
    query = f"""
    [out:json][timeout:12];
    (
      nwr(around:{radius_m},{lat},{lon})[amenity~"^(hospital|clinic|doctors|police|fire_station)$"];
      nwr(around:{radius_m},{lat},{lon})[emergency~"^(ambulance_station|fire_station|ambulance_centre|rescue_station)$"];
    );
    out center tags;
    """
    headers = {"User-Agent": "ResQ-AI public emergency service directory/1.0 (disaster response prototype)"}
    endpoints = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    )
    payload = None
    last_error = None
    # Public Overpass mirrors can be rate-limited. Try POST and GET on each mirror
    # with bounded timeouts before reporting an outage.
    for endpoint in endpoints:
        for method in ("post", "get"):
            try:
                if method == "post":
                    response = requests.post(
                        endpoint, data={"data": query}, headers=headers, timeout=(3, 8)
                    )
                else:
                    response = requests.get(
                        endpoint, params={"data": query}, headers=headers, timeout=(3, 8)
                    )
                response.raise_for_status()
                candidate = response.json()
                if isinstance(candidate, dict) and isinstance(candidate.get("elements"), list):
                    payload = candidate
                    break
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
        if payload is not None:
            break
    labels = {
        "hospital": "Hospital", "clinic": "Clinic", "doctors": "Medical clinic",
        "police": "Police station", "fire_station": "Fire station",
        "ambulance_station": "Ambulance station", "ambulance_centre": "Ambulance centre",
        "rescue_station": "Rescue station", "ambulance": "Ambulance service",
    }

    # Fallback: query Nominatim's public map search within a bounded box if all
    # Overpass mirrors are unavailable. These are directory leads, not live teams.
    fallback_rows = []
    if payload is None:
        headers["Accept-Language"] = "en"
        lat_delta = radius_m / 1000 / 110.574
        cos_lat = max(0.2, abs(math.cos(math.radians(lat))))
        lon_delta = radius_m / 1000 / (111.320 * cos_lat)
        viewbox = f"{lon - lon_delta},{lat + lat_delta},{lon + lon_delta},{lat - lat_delta}"
        for term, service_type in (
            ("hospital", "Hospital"),
            ("clinic", "Medical clinic"),
            ("police station", "Police station"),
            ("fire station", "Fire station"),
            ("ambulance station", "Ambulance station"),
            ("rescue station", "Rescue station"),
        ):
            try:
                response = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": term, "format": "jsonv2", "limit": 10,
                        "viewbox": viewbox, "bounded": 1,
                        "addressdetails": 0,
                    },
                    headers=headers,
                    timeout=(3, 8),
                )
                response.raise_for_status()
                entries = response.json()
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    name = str(entry.get("name") or "").strip()
                    if not name:
                        continue
                    item_lat, item_lon = float(entry["lat"]), float(entry["lon"])
                    fallback_rows.append({
                        "name": name,
                        "type": service_type,
                        "distance_km": _distance_km(lat, lon, item_lat, item_lon),
                        "phone": "",
                        "source": "OpenStreetMap Nominatim public directory",
                    })
            except (requests.RequestException, ValueError, TypeError, KeyError):
                continue
        if not fallback_rows:
            raise requests.RequestException("Overpass and Nominatim public directories are unavailable") from last_error
        unique = {}
        for row in fallback_rows:
            key = (row["name"].casefold(), row["type"])
            if key not in unique or row["distance_km"] < unique[key]["distance_km"]:
                unique[key] = row
        return sorted(unique.values(), key=lambda row: row["distance_km"])[:30]

    labels = {
        "hospital": "Hospital", "clinic": "Clinic", "doctors": "Medical clinic",
        "police": "Police station", "fire_station": "Fire station",
        "ambulance_station": "Ambulance station", "ambulance_centre": "Ambulance centre",
        "rescue_station": "Rescue station", "ambulance": "Ambulance service",
    }
    results = []
    seen = set()
    for item in payload.get("elements", []):
        tags = item.get("tags") or {}
        name = str(tags.get("name") or tags.get("official_name") or "").strip()
        if not name:
            continue
        coords = item if item.get("lat") is not None else (item.get("center") or {})
        if coords.get("lat") is None or coords.get("lon") is None:
            continue
        kind = str(tags.get("amenity") or tags.get("emergency") or "emergency service")
        phone = str(tags.get("contact:phone") or tags.get("phone") or tags.get("contact:mobile") or "").strip()
        distance = _distance_km(lat, lon, float(coords["lat"]), float(coords["lon"]))
        key = (name.casefold(), labels.get(kind, kind.replace("_", " ").title()))
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "name": name,
            "type": labels.get(kind, kind.replace("_", " ").title()),
            "distance_km": distance,
            "phone": phone,
            "source": "OpenStreetMap public directory",
        })
    return sorted(results, key=lambda row: row["distance_km"])[:30]


active_incidents = [
    incident for incident in center.incidents
    if str(incident.get("status") or "").strip().lower() != "resolved"
]

if not active_incidents:
    st.info(
        "No incidents reported yet. Submit an incident through Report Incident to generate an assessment. "
        "No incident, distance, rescue team, hospital, or recommendation will be invented."
    )
    st.stop()

incident_labels = {
    str(item.get("id")): (
        f'{item.get("id")} · {item.get("disaster_type") or "Unclassified"} · '
        f'{item.get("people_affected") or 0:,} people affected'
    )
    for item in active_incidents
    if item.get("id")
}
incident_ids = list(incident_labels)
if not incident_ids:
    st.warning("Incident records were loaded, but none has a usable ID. Please review the saved report.")
    st.stop()

st.markdown("### Reported incident")
selected_id = st.selectbox(
    "Choose a reported incident",
    incident_ids,
    format_func=lambda value: incident_labels[value],
)
incident = next((item for item in active_incidents if str(item.get("id")) == selected_id), {})
# The selected report is the single source of truth for the search location.
# Do not ask the reporter/coordinator to enter the address a second time.
saved_location_text = str(incident.get("location_text") or "").strip()

assignment = center.assignment_for(selected_id)

raw_type = str(incident.get("disaster_type") or "").strip()
is_unclassified = not raw_type or raw_type.lower() in {"unknown", "unclassified", "none", "null"}
incident_type = "Unclassified — review the report details" if is_unclassified else raw_type
people = incident.get("people_affected")
try:
    people_label = f"{int(people):,}" if people is not None and str(people).strip() else "Not provided"
except (TypeError, ValueError):
    people_label = str(people or "Not provided")
lat, lon = incident.get("lat"), incident.get("lon")
# Use the coordinates captured when the incident was reported. The saved address
# is displayed for context; no second location entry or geocoding step is needed.
location_text = saved_location_text
location = location_text or (
    f"{lat}, {lon}"
    if lat is not None and lon is not None
    else "Location not available"
)

a, b, c, d = st.columns(4)
score = incident.get("priority_score")
a.metric("Priority score", f"{score}/100" if score is not None else "Not calculated")
b.metric("People affected", people_label)
c.metric("Incident type", incident_type)
d.metric("Status", str(incident.get("status") or "Active"))

st.markdown("**Reported description**")
description = str(incident.get("description") or incident.get("summary") or "").strip()
if description:
    st.write(description)
else:
    st.warning("This saved incident has no description. Review the original report; the hazard type cannot be verified from this record.")

detail_left, detail_right = st.columns(2)
with detail_left:
    st.markdown("**Reported location**")
    st.write(location_text if location_text else location)
with detail_right:
    st.markdown("**Reported at**")
    st.write(str(incident.get("reported_at") or "Timestamp not available"))

st.divider()
st.markdown("### Nearby hospitals and emergency services")
st.caption(f"Search location: {location_text or location} · nearest first · straight-line distance estimate. Public directory entries do not confirm live availability or dispatch readiness.")
if lat is None or lon is None:
    st.warning("This incident has no usable coordinates. Reopen the report and enter its location before searching nearby services.")
else:
    try:
        with st.spinner("Searching public service directories near the incident…"):
            nearby_services = _nearby_public_services(float(lat), float(lon))
        if nearby_services:
            for service in nearby_services:
                service_cols = st.columns([3, 1, 2])
                service_cols[0].markdown(f"**{service['name']}**")
                service_cols[0].caption(service["type"])
                service_cols[1].markdown(f"{service['distance_km']:.1f} km")
                service_cols[2].markdown(service["phone"] if service["phone"] else "Contact number not listed")
                if service["phone"]:
                    service_cols[2].caption("Publicly listed number; call to confirm.")
            st.caption("Source: OpenStreetMap public directory. Contact details are displayed only when listed; they are not independently phone-verified by ResQ-AI.")
        else:
            st.warning("No nearby hospitals or emergency-service locations were found in the public directory within 25 km. Contact local emergency services directly.")
    except Exception:
        st.warning("The public service directory could not be reached right now. No facilities or phone numbers have been invented. Please contact local emergency services directly.")

st.markdown("### Nearby emergency response stations")
st.caption("Fire, police and ambulance facilities are shown as public-directory leads, not as confirmed dispatch-ready teams.")
response_station_types = {"Fire station", "Police station", "Ambulance station", "Ambulance centre", "Rescue station", "Ambulance service"}
response_stations = [
    service for service in (nearby_services if lat is not None and lon is not None and "nearby_services" in locals() else [])
    if service["type"] in response_station_types
]
if response_stations:
    for service in response_stations:
        rc = st.columns([3, 1, 2])
        rc[0].markdown(f"**{service['name']}**")
        rc[0].caption(service["type"])
        rc[1].markdown(f"{service['distance_km']:.1f} km")
        rc[2].markdown(service["phone"] if service["phone"] else "Contact number not listed")
    st.caption("These listings do not verify whether a crew is on duty, equipped, or available to dispatch.")
else:
    st.info("No nearby response stations could be confirmed from the public directory in this lookup. This is not proof that no stations exist. ResQ-AI has no connected live roster to verify individual rescue teams.")
verified_resources = [
    resource for resource in center.resources
    if str(resource.get("status") or "").strip().lower() == "available"
    and resource.get("source") in {"operator-verified-upload", "trusted-live-feed", "official-feed"}
]
if verified_resources:
    st.markdown("**Connected verified resource records**")
    resource_rows = []
    for resource in verified_resources:
        if resource.get("lat") is None or resource.get("lon") is None or lat is None or lon is None:
            continue
        resource_rows.append({
            "name": str(resource.get("name") or resource.get("id") or "Unnamed team"),
            "type": str(resource.get("type") or "Rescue team").replace("_", " ").title(),
            "distance_km": _distance_km(float(lat), float(lon), float(resource["lat"]), float(resource["lon"])),
            "phone": str(resource.get("phone") or resource.get("contact_phone") or "").strip(),
        })
    for resource in sorted(resource_rows, key=lambda row: row["distance_km"]):
        rc = st.columns([3, 1, 2])
        rc[0].markdown(f"**{resource['name']}**")
        rc[0].caption(resource["type"])
        rc[1].markdown(f"{resource['distance_km']:.1f} km")
        rc[2].markdown(resource["phone"] if resource["phone"] else "Contact number not listed")

if is_unclassified:
    st.warning(
        "The saved report is not classified as a known hazard. ResQ-AI will not guess the incident type. "
        "Review or resubmit the report with the hazard and location clearly described."
    )

st.markdown("### General response guidance")
action = str(incident.get("recommended_action") or "").strip()
if action:
    st.info(action.replace("Recommended action:", "Suggested guidance:", 1))
    st.caption("Guidance only — this does not confirm a dispatch or verify on-scene conditions.")
else:
    st.info("No response guidance has been generated for this report yet.")

if assignment and assignment.get("reason"):
    st.caption(str(assignment["reason"]))

st.markdown("### Resource readiness")
st.caption(
    "Incident assessment and resource availability are separate. Public facility listings do not show live bed capacity or confirm dispatch readiness."
)

counts = {
    "Active reported incidents": len(active_incidents),
    "Verified resource records loaded": len(center.resources),
    "Shelter records loaded": len(center.shelters),
}
cols = st.columns(len(counts))
for col, (label, count) in zip(cols, counts.items()):
    col.metric(label, count)

if not center.resources:
    st.error(
        "Resource allocation unavailable: no verified rescue-team inventory is connected. "
        "No team name, distance, ambulance, or medication availability can be recommended until "
        "real resource records or a trusted live feed is configured."
    )
elif not assignment or not assignment.get("resource_id"):
    st.warning(
        "No eligible nearby resource has been assigned from the currently loaded records. "
        "Check verified resource coordinates, capabilities, capacity, and current availability."
    )
else:
    resource_id = assignment.get("resource_id")
    resource_name = assignment.get("resource_name")
    distance = assignment.get("distance_km")
    if resource_id and resource_name and isinstance(distance, (int, float)):
        st.success(f"Candidate resource: {resource_name} ({resource_id}) · {distance:.2f} km")
        st.caption("This is a decision-support candidate, not a confirmed dispatch.")

if assignment and (assignment.get("hospital_name") or assignment.get("hospital_id")):
    hospital_name = str(assignment.get("hospital_name") or assignment.get("hospital_id"))
    hospital_distance = assignment.get("hospital_km")
    if assignment.get("hospital_availability") == "capacity-reported":
        st.success(
            f"Hospital candidate with operator-reported capacity: {hospital_name}"
            + (f" · {hospital_distance:.2f} km" if isinstance(hospital_distance, (int, float)) else "")
        )
        st.caption("Capacity is operator-reported and must be confirmed by the hospital before transfer.")
    else:
        st.info(
            f"Nearby hospital directory lead: {hospital_name}"
            + (f" · {hospital_distance:.2f} km" if isinstance(hospital_distance, (int, float)) else "")
        )
        st.warning(
            "This is a public facility-directory match, not a verified available bed or dispatch destination. "
            "Call the facility to confirm emergency capability and current capacity."
        )
if center.shelters and assignment and (assignment.get("shelter_name") or assignment.get("shelter_id")):
    st.write("**Shelter candidate:** " + str(assignment.get("shelter_name") or assignment.get("shelter_id")))
elif not center.shelters:
    st.caption("No verified shelter inventory is connected.")


# What-if simulations operate on a copy of the current state. They never overwrite
# submitted reports or persist simulated changes to the operational inventory.
from core.state import CommandCenter

st.divider()
st.markdown("### What-if response simulation")
st.caption(
    "Choose the incident above, change one condition, and compare the response plan. "
    "These are hypothetical changes only; they do not dispatch teams or alter saved records."
)

scenario_options = [
    "Increase estimated people affected",
    "Mark a resource unavailable",
    "Block a road",
    "Reduce reported hospital beds",
    "Increase shelter occupancy",
]
scenario_kind = st.selectbox(
    "Scenario condition",
    scenario_options,
    key="scenario_condition",
)

scenario_value = None
scenario_target = None
scenario_ready = True

if scenario_kind == "Increase estimated people affected":
    current_people = max(0, int(incident.get("people_affected") or 0))
    scenario_value = st.number_input(
        "Hypothetical people affected",
        min_value=0,
        value=current_people,
        step=1,
        key=f"scenario_people_{selected_id}",
    )
elif scenario_kind == "Mark a resource unavailable":
    if not center.resources:
        st.info("No resource inventory is connected, so this scenario cannot be tested yet.")
        scenario_ready = False
    else:
        resource_options = {
            str(r.get("id")): f"{r.get('name') or r.get('id')} · {r.get('status') or 'Status unknown'}"
            for r in center.resources if r.get("id")
        }
        scenario_target = st.selectbox(
            "Resource to mark unavailable",
            list(resource_options),
            format_func=lambda value: resource_options[value],
            key="scenario_resource",
        )
elif scenario_kind == "Block a road":
    if not center.roads:
        st.info("No road-segment inventory is connected. Upload verified road data before testing road closures.")
        scenario_ready = False
    else:
        road_options = {
            str(r.get("id")): f"{r.get('name') or r.get('id')} · {r.get('status') or 'Status unknown'}"
            for r in center.roads if r.get("id")
        }
        scenario_target = st.selectbox(
            "Road segment to block",
            list(road_options),
            format_func=lambda value: road_options[value],
            key="scenario_road",
        )
elif scenario_kind == "Reduce reported hospital beds":
    hospital_options = {
        str(h.get("id")): f"{h.get('name') or h.get('id')} · {int(h.get('available_beds') or 0)} reported beds"
        for h in center.hospitals
        if h.get("id") and str(h.get("source_type") or "") != "public_reference_directory"
        and h.get("available_beds") is not None
    }
    if not hospital_options:
        st.info("No operator-reported hospital capacity is connected. Public directory locations do not provide live bed counts.")
        scenario_ready = False
    else:
        scenario_target = st.selectbox(
            "Hospital capacity to change",
            list(hospital_options),
            format_func=lambda value: hospital_options[value],
            key="scenario_hospital",
        )
        current_beds = next(
            (int(h.get("available_beds") or 0) for h in center.hospitals if str(h.get("id")) == scenario_target),
            0,
        )
        scenario_value = st.number_input(
            "Hypothetical available beds",
            min_value=0,
            value=current_beds,
            step=1,
            key=f"scenario_beds_{scenario_target}",
        )
elif scenario_kind == "Increase shelter occupancy":
    shelter_options = {
        str(s.get("id")): f"{s.get('name') or s.get('id')} · {int(s.get('occupied') or 0)}/{int(s.get('capacity') or 0)} occupied"
        for s in center.shelters if s.get("id")
    }
    if not shelter_options:
        st.info("No verified shelter capacity records are connected.")
        scenario_ready = False
    else:
        scenario_target = st.selectbox(
            "Shelter to change",
            list(shelter_options),
            format_func=lambda value: shelter_options[value],
            key="scenario_shelter",
        )
        shelter = next((s for s in center.shelters if str(s.get("id")) == scenario_target), {})
        scenario_value = st.number_input(
            "Hypothetical occupied spaces",
            min_value=0,
            max_value=max(0, int(shelter.get("capacity") or 0)),
            value=min(
                max(0, int(shelter.get("occupied") or 0)),
                max(0, int(shelter.get("capacity") or 0)),
            ),
            step=1,
            key=f"scenario_occupancy_{scenario_target}",
        )

if st.button(
    "Simulate and compare response plan",
    type="primary",
    use_container_width=True,
    disabled=not scenario_ready,
    key="run_response_scenario",
):
    simulated = CommandCenter.from_dict(center.to_dict())
    try:
        if scenario_kind == "Increase estimated people affected":
            simulated.bump_people(selected_id, int(scenario_value))
        elif scenario_kind == "Mark a resource unavailable":
            simulated.set_resource_status(str(scenario_target), "Unavailable")
        elif scenario_kind == "Block a road":
            simulated.set_road_status(str(scenario_target), "Blocked")
        elif scenario_kind == "Reduce reported hospital beds":
            simulated.set_hospital_beds(str(scenario_target), int(scenario_value))
        elif scenario_kind == "Increase shelter occupancy":
            simulated.set_shelter_occupied(str(scenario_target), int(scenario_value))

        before = center.assignment_for(selected_id) or {}
        after = simulated.assignment_for(selected_id) or {}
        before_name = before.get("resource_name") or "No eligible resource"
        after_name = after.get("resource_name") or "No eligible resource"
        before_distance = before.get("distance_km")
        after_distance = after.get("distance_km")

        st.markdown("#### Response plan comparison")
        left, right = st.columns(2)
        with left:
            st.markdown("**Current conditions**")
            st.metric("Candidate resource", str(before_name))
            st.metric(
                "Estimated distance",
                f"{before_distance:.2f} km" if isinstance(before_distance, (int, float)) else "Unavailable",
            )
            st.caption(str(before.get("reason") or "No allocation reason available."))
        with right:
            st.markdown("**Simulated conditions**")
            st.metric(
                "Candidate resource",
                str(after_name),
                delta=("Changed" if before_name != after_name else "Unchanged"),
                delta_color="off",
            )
            st.metric(
                "Estimated distance",
                f"{after_distance:.2f} km" if isinstance(after_distance, (int, float)) else "Unavailable",
            )
            st.caption(str(after.get("reason") or "No allocation reason available."))

        if before_name != after_name or before_distance != after_distance:
            st.warning("The hypothetical condition changes the candidate plan. A human coordinator must verify all details.")
        else:
            st.info("The selected resource recommendation did not change under this scenario. Review the reason and inventory assumptions.")
        if after.get("hospital_name") or after.get("hospital_id"):
            st.write(
                "**Hospital lead after simulation:** "
                + str(after.get("hospital_name") or after.get("hospital_id"))
                + (
                    f" · {after.get('hospital_km'):.2f} km"
                    if isinstance(after.get("hospital_km"), (int, float))
                    else ""
                )
            )
            if after.get("hospital_availability") != "capacity-reported":
                st.caption("Hospital availability remains unverified; a directory match is not a confirmed bed.")
        st.caption("Simulation only — no report, inventory, dispatch, or saved response plan was changed.")
    except (TypeError, ValueError, KeyError) as exc:
        st.error(f"Could not run this scenario: {exc}")
