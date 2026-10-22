from __future__ import annotations

import json
import math
from pathlib import Path
import requests
import streamlit as st

from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar
from core.config import CITY_LAT, CITY_LON
from core.persistence import is_configured, save_incident
from utils.validation import validate_report

def _geocode_location(address: str) -> tuple[float, float] | None:
    """Convert a user-entered address into latitude/longitude."""
    address = address.strip()
    if not address:
        return None
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


page_setup("Report Incident")

center = get_center()
render_sidebar(center)
render_header(center, "Submit an emergency report · NLP extracts facts · the priority engine scores independently")

@st.cache_data(show_spinner=False)
def _load_india_locations() -> list[dict]:
    """Load the bundled India state/UT and district directory."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "india_states_districts.min.json"
    with data_path.open("r", encoding="utf-8") as file:
        return json.load(file)


india_locations = _load_india_locations()
state_names = [item["name"] for item in india_locations]
lat = float(CITY_LAT)
lon = float(CITY_LON)
selected_address = ""

with st.form("report_form"):
    description = st.text_area("Incident description", placeholder="Describe what happened, hazards, and people affected", height=140)
    st.markdown("#### Incident location")
    st.caption("Select the Indian state/UT and district, then enter the city and the most precise address or landmark available.")
    state_name = st.selectbox("State / Union Territory", state_names, index=state_names.index("Uttar Pradesh") if "Uttar Pradesh" in state_names else 0)
    selected_state = next(item for item in india_locations if item["name"] == state_name)
    district_names = sorted(district["name"] for district in selected_state.get("districts", []))
    district_name = st.selectbox("District", district_names)
    city_name = st.text_input("City / Town / Village", placeholder="e.g., Noida")
    manual_address = st.text_input(
        "Full address / landmark",
        placeholder="e.g., Sector 18 Metro Station, near Gate 2",
        help="Add a street, sector, building, landmark, or other detail that helps responders locate the incident."
    )
    with st.expander("Advanced: coordinates (only if address lookup fails)"):
        coord_cols = st.columns(2)
        manual_lat = coord_cols[0].number_input(
            "Latitude", min_value=-90.0, max_value=90.0, value=float(CITY_LAT), format="%.6f"
        )
        manual_lon = coord_cols[1].number_input(
            "Longitude", min_value=-180.0, max_value=180.0, value=float(CITY_LON), format="%.6f"
        )
        st.caption("Coordinates start at the configured city centre. If geocoding fails, enter the actual incident coordinates before submitting.")
    people = st.number_input("Estimated people affected", min_value=0, value=0, step=1)
    accessibility = st.selectbox("Observed accessibility", ["Open", "Restricted", "Blocked"], index=0)
    reporter = st.text_input("Reporter (optional)", placeholder="Name or call sign")
    image = st.file_uploader("Optional image (stored for operator review only — no computer vision in this MVP)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("ANALYZE INCIDENT", use_container_width=True)

if submitted:
    city_name = city_name.strip()
    landmark = manual_address.strip()
    location_parts = [part for part in [landmark, city_name, district_name, state_name, "India"] if part]
    selected_address = ", ".join(location_parts)
    lat = float(manual_lat)
    lon = float(manual_lon)
    if not city_name:
        errors = ["Enter the incident city, town, or village."]
    else:
        with st.spinner("Locating the selected Indian address…"):
            geocoded = _geocode_location(selected_address)
        if geocoded:
            lat, lon = geocoded
            st.success(f"Location found for: {selected_address}")
        else:
            st.warning("Could not automatically locate this address. Using the coordinates in Advanced settings; please confirm they match the incident location.")
        errors = validate_report(description, people, lat, lon)
    if errors:
        for err in errors:
            st.error(err)
    else:
        image_name = image.name if image is not None else ""
        saved_permanently = False
        save_error = None
        with st.status("Analyzing incident…", expanded=True) as status:
            st.write("Running NLP extraction (LLM if configured, otherwise fallback)…")
            result = center.analyze_and_add_incident(
                description=description,
                people_affected=int(people),
                lat=float(lat),
                lon=float(lon),
                accessibility=accessibility,
                reporter=reporter,
                image_name=image_name,
                location_text=selected_address,
            )
            analysis = result["analysis"]
            incident = result["incident"]
            assignment = result["assignment"]

            # Persistence is optional for the submission build. If the database
            # is not configured or could not be reached at session startup, keep the
            # report usable in this session and defer durable storage setup.
            if st.session_state.get("incident_store_configured", False):
                try:
                    saved_permanently = save_incident(incident, analysis, assignment)
                except Exception as exc:
                    # Keep the current-session report visible, but never claim it was saved.
                    save_error = type(exc).__name__

            persist(center)
            if not st.session_state.get("incident_store_configured", False):
                saved_permanently = False
            if saved_permanently:
                st.session_state.incident_store_error = None
                status.update(label="Analysis complete · report saved", state="complete")
            elif save_error:
                st.session_state.incident_store_error = (
                    "The incident database save failed. The report is only in this session."
                )
                status.update(label="Analysis complete · database save failed", state="error")
            else:
                st.session_state.incident_store_error = None
                status.update(label="Analysis complete · session-only", state="complete")

        if saved_permanently:
            st.toast(f"{incident['id']} saved to the incident database")
            st.success(f"Analysis complete · {center.ai_mode} · report saved permanently")
        elif save_error:
            st.error(
                "Analysis completed, but the report was NOT saved permanently. "
                f"Database error type: {save_error}. Check the DATABASE_URL secret and "
                "confirm the Supabase table migration has been run. This report will disappear "
                "after the current session ends."
            )
        else:
            st.caption("Database storage is not connected; this report is session-only.")

        # Human-readable incident summary; raw structured output stays optional.
        st.markdown("### Incident assessment")
        score = int(incident.get("priority_score") or 0)
        urgency = str(incident.get("urgency") or "Unknown")
        urgency_color = {
            "Critical": "#e11d48",
            "High": "#ea580c",
            "Medium": "#ca8a04",
            "Low": "#0d9488",
        }.get(urgency, "#64748b")

        st.markdown(
            f"""
            <div style="
                padding:18px 20px; border-radius:16px;
                border:1px solid {urgency_color}55;
                background:linear-gradient(115deg,{urgency_color}14,rgba(20,184,166,.06));
                margin:4px 0 16px;">
              <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
                <div>
                  <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.72;">Incident ID</div>
                  <div style="font-size:25px;font-weight:750;">{incident['id']}</div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.72;">Priority score</div>
                  <div style="font-size:28px;font-weight:800;color:{urgency_color};">{score}<span style="font-size:15px;opacity:.7;"> / 100</span></div>
                  <span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{urgency_color}20;color:{urgency_color};font-weight:700;font-size:12px;">{urgency.upper()}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        fact_cols = st.columns(3)
        fact_cols[0].metric("Disaster type", str(analysis.get("disaster_type") or "Unknown"))
        fact_cols[1].metric("Severity", f"{analysis.get('severity', '—')}/5")
        fact_cols[2].metric("People affected", f"{analysis.get('people_affected', people):,}")

        fact_cols = st.columns(3)
        fact_cols[0].metric(
            "Medical emergency",
            "Detected" if analysis.get("medical_emergency") else "Not detected",
        )
        fact_cols[1].metric("Access", str(analysis.get("accessibility") or accessibility))
        fact_cols[2].metric("Vulnerable people", f"{incident.get('vulnerable_population') or 0:,}")

        if assignment:
            st.markdown("### Resource and destination recommendation")
            rec_cols = st.columns(3)
            rec_cols[0].metric(
                "Recommended resource",
                str(assignment.get("resource_id") or "Unassigned"),
                help=str(assignment.get("resource_name") or ""),
            )
            rec_cols[1].metric("Hospital", str(assignment.get("hospital_id") or "None"))
            rec_cols[2].metric("Shelter", str(assignment.get("shelter_id") or "None"))
            if assignment.get("distance_km") is not None:
                st.caption(
                    f"Prototype distance: {assignment['distance_km']} km. "
                    f"{assignment.get('reason') or ''}"
                )
            st.caption("A coordinator must verify the recommendation before operational use.")
        else:
            st.warning("No resource assignment is currently available. A coordinator should review the incident.")

        with st.expander("View extracted structured data (JSON)", expanded=False):
            st.caption("Technical view for debugging and review. This is data, not executable code.")
            st.json(
                {
                    "disaster_type": analysis.get("disaster_type"),
                    "severity": analysis.get("severity"),
                    "people_affected": analysis.get("people_affected"),
                    "medical_emergency": analysis.get("medical_emergency"),
                    "accessibility": analysis.get("accessibility"),
                    "urgency": incident.get("urgency"),
                    "vulnerable_population": incident.get("vulnerable_population", 0),
                }
            )

        st.caption("Use Incident Operations to review response actions and Situation Reports for the consolidated operational summary.")

st.divider()
st.caption("Reports entered here are operator-submitted and are not independently verified. Confirm the selected pin is accurate before submitting.")
