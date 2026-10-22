from __future__ import annotations

import os

import streamlit as st

from components.google_location_picker import google_location_picker
from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar
from core.config import CITY_LAT, CITY_LON
from core.persistence import is_configured, save_incident
from utils.validation import validate_report

page_setup("Report Incident")

center = get_center()
render_sidebar(center)
render_header(center, "Submit an emergency report · NLP extracts facts · the priority engine scores independently")

st.info(
    "The language model (or fallback keyword engine) extracts structured facts. "
    "It does not choose the final rescue unit. Priority scoring and assignment are deterministic."
)

try:
    google_maps_api_key = str(st.secrets.get("GOOGLE_MAPS_API_KEY", "")).strip()
except Exception:
    google_maps_api_key = ""
google_maps_api_key = google_maps_api_key or os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

st.markdown("### Select incident location")
st.caption("Search for an address or landmark, click the map, or drag the pin to the exact incident location.")
selected_location = None
if google_maps_api_key:
    selected_location = google_location_picker(
        api_key=google_maps_api_key,
        default_lat=CITY_LAT,
        default_lon=CITY_LON,
        key="report_incident_google_map",
    )
else:
    st.warning(
        "Google Maps is not configured yet. Add GOOGLE_MAPS_API_KEY to Streamlit secrets "
        "and enable Maps JavaScript API and Places API to use the location picker."
    )
    st.link_button(
        "Open Google Maps",
        "https://maps.google.com/",
        use_container_width=False,
    )

if isinstance(selected_location, dict) and selected_location.get("lat") is not None and selected_location.get("lon") is not None:
    lat = float(selected_location["lat"])
    lon = float(selected_location["lon"])
    selected_address = str(selected_location.get("address") or "Map location selected")
    st.success(f"Selected location: {selected_address}")
    st.caption(f"Coordinates: {lat:.6f}, {lon:.6f}")
else:
    lat = 0.0
    lon = 0.0
    selected_address = ""

with st.form("report_form"):
    description = st.text_area("Incident description", placeholder="Describe what happened, hazards, and people affected", height=140)
    if selected_address:
        st.text_input("Selected incident location", value=selected_address, disabled=True)
    else:
        st.info("Select the incident location on the map above before submitting the report.")
    people = st.number_input("Estimated people affected", min_value=0, value=0, step=1)
    accessibility = st.selectbox("Observed accessibility", ["Open", "Restricted", "Blocked"], index=0)
    reporter = st.text_input("Reporter (optional)", placeholder="Name or call sign")
    image = st.file_uploader("Optional image (stored for operator review only — no computer vision in this MVP)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("ANALYZE INCIDENT", use_container_width=True)

if submitted:
    if not selected_address or not isinstance(selected_location, dict):
        st.error("Select a precise incident location on the Google Map before submitting.")
        errors = []
    else:
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
            )
            analysis = result["analysis"]
            incident = result["incident"]
            assignment = result["assignment"]

            try:
                saved_permanently = save_incident(incident, analysis, assignment)
            except Exception as exc:
                # Keep the current-session report visible, but never claim it was saved.
                save_error = type(exc).__name__

            persist(center)
            st.session_state.incident_store_configured = is_configured()
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

        st.markdown("### Why this priority?")
        st.caption("The score is calculated by predefined rules. It is decision support, not an automatic dispatch decision.")
        for item in incident.get("priority_breakdown") or []:
            label = str(item.get("label") or "Factor")
            points = int(item.get("points") or 0)
            detail = str(item.get("detail") or "")
            col_label, col_points = st.columns([5, 1])
            col_label.markdown(f"**{label}**")
            col_label.caption(detail)
            col_points.markdown(f"**+{points}**")
            st.progress(min(100, max(0, points * 3)), text=f"{points} points")

        action = incident.get("recommended_action") or "No recommended action available."
        st.markdown("### Recommended response")
        st.info(action)

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
