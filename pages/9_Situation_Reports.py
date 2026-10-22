from __future__ import annotations
import streamlit as st
from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar
from core.reporting import (
    event_log_pdf,
    full_snapshot_pdf,
    incident_register_pdf,
    situation_report_pdf,
)

page_setup("Situation Reports")
center = get_center()
render_sidebar(center)
render_header(center, "Exportable operational picture · source-labelled prototype data")
st.info("Reports are generated from the current command-center snapshot. Live government alerts are not automatically mixed into incident reports.")
m = center.metrics()
a,b,c,d = st.columns(4)
a.metric("Active incidents", m.get("active_incidents", 0))
b.metric("Critical", m.get("critical_incidents", 0))
c.metric("Available resources", m.get("available_resources", 0))
d.metric("Shelter spaces", m.get("shelter_spaces_available", 0))
st.markdown("### Download reports")
left_reports, right_reports = st.columns(2, gap="large")
with left_reports:
    with st.container(border=True):
        st.markdown("#### Situation report")
        st.caption("Key metrics, priority incidents, and recommended assignments.")
        st.download_button("Download situation report PDF", situation_report_pdf(center), "resq_situation_report.pdf", "application/pdf", use_container_width=True)
    with st.container(border=True):
        st.markdown("#### Incident register")
        st.caption("Prioritized incident details, impact, location, and recommended actions.")
        st.download_button("Download incident register PDF", incident_register_pdf(center), "resq_incident_register.pdf", "application/pdf", use_container_width=True)
with right_reports:
    with st.container(border=True):
        st.markdown("#### Full snapshot")
        st.caption("Incidents, assignments, resources, facilities, roads, and recent events.")
        st.download_button("Download full snapshot PDF", full_snapshot_pdf(center), "resq_full_snapshot.pdf", "application/pdf", use_container_width=True)
    with st.container(border=True):
        st.markdown("#### Audit and event log")
        st.caption("Timestamped command-center events for review and record keeping.")
        st.download_button("Download audit log PDF", event_log_pdf(center), "resq_audit_event_log.pdf", "application/pdf", use_container_width=True)
st.markdown("### Current incident register")
st.dataframe([{"ID":r.get("id"),"Type":r.get("disaster_type"),"Priority":r.get("priority_score"),"Urgency":r.get("urgency"),"Status":r.get("workflow_status") or r.get("status"),"People affected":r.get("people_affected"),"Medical":r.get("medical_emergency"),"Source":r.get("source")} for r in sorted(center.incidents,key=lambda x:int(x.get("priority_score") or 0),reverse=True)], use_container_width=True, hide_index=True)
st.caption("Do not share personal or sensitive incident data outside authorized response channels.")
