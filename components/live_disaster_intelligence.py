"""Unified global hazard monitoring from connected public feeds."""
from __future__ import annotations

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from core.gdacs_feed import GDACS_SOURCE_URL, fetch_gdacs_events
from core.live_feeds import USGS_ALL_DAY_URL, fetch_usgs_earthquakes
from core.live_data import IMD_PUBLIC_CAP_URL, get_imd_live_data, get_ndma_cap_alerts
from core.alert_translation import english_text


@st.cache_data(ttl=300, show_spinner=False)
def _cached_gdacs(lookback_days: int) -> dict:
    return fetch_gdacs_events(lookback_days=lookback_days)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_usgs() -> dict:
    return fetch_usgs_earthquakes()


@st.fragment(run_every=300)
def render_live_disaster_intelligence() -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / GLOBAL MONITORING</div>', unsafe_allow_html=True)
    st.title("Live Disaster Intelligence")
    st.caption(
        "A map-first view of source-reported global hazards from GDACS and USGS, alongside India government alerts from IMD and NDMA SACHET when their feeds are available. "
        "These public feeds do not confirm local damage, casualties, or dispatch requirements."
    )

    controls, refresh_slot = st.columns([4, 1], vertical_alignment="bottom")
    with controls:
        lookback = st.selectbox(
            "GDACS event window", [7, 30, 90], index=1,
            format_func=lambda value: f"Past {value} days",
        )
    with refresh_slot:
        force_refresh = st.button("Refresh feeds", type="primary", use_container_width=True)
        if force_refresh:
            _cached_gdacs.clear()
            _cached_usgs.clear()

    source_rows = []
    events = []
    failures = []
    with st.spinner("Retrieving source-reported hazard events…"):
        try:
            # Bypass Streamlit's cache when the user explicitly requests a refresh.
            gdacs = fetch_gdacs_events(lookback_days=lookback) if force_refresh else _cached_gdacs(lookback)
            gdacs_events = gdacs.get("events", [])
            latest_gdacs_update = max(
                (str(event.get("updated_at_utc") or event.get("started_at_utc") or "")
                 for event in gdacs_events),
                default="",
            ) or "Not provided"
            source_rows.append({
                "Source": "GDACS",
                "Status": "Connected",
                "Events": gdacs.get("event_count", len(gdacs_events)),
                "Retrieved by app (UTC)": gdacs.get("fetched_at_utc", "Not provided"),
                "Latest event update/start (UTC)": latest_gdacs_update,
                "Official source": GDACS_SOURCE_URL,
            })
            for event in gdacs.get("events", []):
                events.append({
                    "Hazard": event.get("event_type", "Hazard"),
                    "Event": event.get("name", "Name not provided"),
                    "Area": event.get("country", "Not provided"),
                    "Alert / magnitude": event.get("alert_level", "Not reported"),
                    "Event time (UTC)": event.get("started_at_utc") or "Not provided",
                    "Source": "GDACS",
                    "Record": event.get("source_url") or GDACS_SOURCE_URL,
                    "Latitude": event.get("latitude"),
                    "Longitude": event.get("longitude"),
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            failures.append(("GDACS", type(exc).__name__, GDACS_SOURCE_URL))
            source_rows.append({
                "Source": "GDACS", "Status": "Unavailable", "Events": "—",
                "Retrieved by app (UTC)": "—", "Latest event update/start (UTC)": "—", "Official source": GDACS_SOURCE_URL,
            })

        try:
            usgs = fetch_usgs_earthquakes() if force_refresh else _cached_usgs()
            usgs_generated = usgs.get("feed_generated_at_utc", "Not provided")
            source_rows.append({
                "Source": "USGS Earthquake Hazards Program",
                "Status": "Connected",
                "Events": usgs.get("event_count", len(usgs.get("events", []))),
                "Retrieved by app (UTC)": usgs.get("fetched_at_utc", "Not provided"),
                "Source feed generated (UTC)": usgs_generated,
                "Official source": USGS_ALL_DAY_URL,
            })
            for event in usgs.get("events", []):
                magnitude = event.get("magnitude")
                events.append({
                    "Hazard": "Earthquake",
                    "Event": event.get("location", "Location not provided"),
                    "Area": "Not provided",
                    "Alert / magnitude": f"Magnitude {magnitude}" if magnitude is not None else "Not reported",
                    "Event time (UTC)": event.get("time_utc") or "Not provided",
                    "Source": "USGS",
                    "Record": event.get("detail_url") or USGS_ALL_DAY_URL,
                    "Latitude": event.get("latitude"),
                    "Longitude": event.get("longitude"),
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            failures.append(("USGS", type(exc).__name__, USGS_ALL_DAY_URL))
            source_rows.append({
                "Source": "USGS Earthquake Hazards Program", "Status": "Unavailable",
                "Events": "—", "Retrieved by app (UTC)": "—", "Source feed generated (UTC)": "—", "Official source": USGS_ALL_DAY_URL,
            })

    # Include India-specific official feeds alongside global hazard feeds. Never invent
    # missing alerts; only display records actually returned by the connected source.
    try:
        imd_india = get_imd_live_data()
        public_result = imd_india.get("public_alerts", {})
        imd_alerts = public_result.get("alerts", [])
        source_rows.append({
            "Source": "India Meteorological Department — public CAP",
            "Status": "Connected" if public_result.get("ok") else "Unavailable",
            "Events": len(imd_alerts),
            "Retrieved by app (UTC)": public_result.get("fetched_at") or "Not provided",
            "Latest event update/start (UTC)": "Not provided",
            "Official source": public_result.get("source_url") or IMD_PUBLIC_CAP_URL,
        })
        for row in imd_alerts:
            title = english_text(row.get("title", ""))
            if not title:
                continue
            summary = english_text(row.get("summary", ""))
            area = english_text(row.get("area", ""))
            events.append({
                "Hazard": english_text(row.get("severity", "")) or "Government alert",
                "Event": title,
                "Area": area or "Location not provided",
                "Alert / magnitude": summary or "See official alert",
                "Event time (UTC)": row.get("published") or "Not provided",
                "Source": "IMD public CAP",
                "Record": row.get("link") or public_result.get("source_url") or IMD_PUBLIC_CAP_URL,
                "Latitude": None,
                "Longitude": None,
            })
    except (requests.RequestException, ValueError, TypeError):
        source_rows.append({
            "Source": "India Meteorological Department — public CAP",
            "Status": "Unavailable", "Events": "—",
            "Retrieved by app (UTC)": "—", "Latest event update/start (UTC)": "—",
            "Official source": IMD_PUBLIC_CAP_URL,
        })

    try:
        ndma = get_ndma_cap_alerts()
        ndma_alerts = ndma.get("alerts", [])
        source_rows.append({
            "Source": "NDMA SACHET / CAP",
            "Status": "Connected" if ndma.get("ok") else "Unavailable",
            "Events": len(ndma_alerts),
            "Retrieved by app (UTC)": ndma.get("fetched_at") or "Not provided",
            "Latest event update/start (UTC)": "Not provided",
            "Official source": ndma.get("source_url") or "https://sachet.ndma.gov.in/",
        })
        for row in ndma_alerts:
            title = english_text(row.get("title", ""))
            if not title:
                continue
            summary = english_text(row.get("summary", ""))
            area = english_text(row.get("area", ""))
            events.append({
                "Hazard": english_text(row.get("severity", "")) or "Government alert",
                "Event": title,
                "Area": area or "Location not provided",
                "Alert / magnitude": summary or "See official alert",
                "Event time (UTC)": row.get("published") or "Not provided",
                "Source": "NDMA SACHET / CAP",
                "Record": row.get("link") or ndma.get("source_url") or "https://sachet.ndma.gov.in/",
                "Latitude": None,
                "Longitude": None,
            })
    except (requests.RequestException, ValueError, TypeError):
        source_rows.append({
            "Source": "NDMA SACHET / CAP", "Status": "Unavailable", "Events": "—",
            "Retrieved by app (UTC)": "—", "Latest event update/start (UTC)": "—",
            "Official source": "https://sachet.ndma.gov.in/",
        })

    connected = sum(row["Status"] == "Connected" for row in source_rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Source-reported records", len(events))
    c2.metric("Feeds connected", f"{connected} / {len(source_rows)}")
    c3.metric("Monitoring window", f"{lookback} days + USGS past day")

    with st.expander("Data-source health", expanded=bool(failures) or force_refresh):
        st.dataframe(
            pd.DataFrame(source_rows), use_container_width=True, hide_index=True,
            column_config={"Official source": st.column_config.LinkColumn("Official source", display_text="Open source")},
        )
        for name, reason, url in failures:
            st.warning(f"{name} is unavailable ({reason}). No example events were substituted. [Open official source]({url})")
        st.caption(
            "App retrieval time means when this app received the response; it does not mean every event is new. "
            "GDACS may continue listing ongoing alerts, while USGS provides a rolling past-day earthquake feed."
        )
        if force_refresh:
            st.success("Refresh requested: both feeds were fetched directly, bypassing the five-minute cache.")
        else:
            st.caption("This view automatically rechecks connected feeds every 5 minutes while the page remains open. Source adapters may cache responses for up to 5 minutes; no polling occurs when the app is closed.")

    if not events:
        if failures:
            st.error("No hazard records could be retrieved from the connected feeds.")
        else:
            st.info("Connected feeds returned no events for these windows.")
        st.caption("Feed retrieval is cached for up to five minutes. Use Refresh feeds to bypass the cache and request fresh data.")
        return

    df = pd.DataFrame(events)
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        hazard_options = ["All hazards"] + sorted(df["Hazard"].dropna().astype(str).unique().tolist())
        selected_hazard = st.selectbox("Hazard type", hazard_options)
    with f2:
        source_options = ["All sources"] + sorted(df["Source"].dropna().astype(str).unique().tolist())
        selected_source = st.selectbox("Data source", source_options)
    with f3:
        query = st.text_input("Search event or location", placeholder="Search event name, area, or alert")

    filtered = df.copy()
    if selected_hazard != "All hazards":
        filtered = filtered[filtered["Hazard"] == selected_hazard]
    if selected_source != "All sources":
        filtered = filtered[filtered["Source"] == selected_source]
    if query.strip():
        term = query.strip().casefold()
        searchable = filtered[["Hazard", "Event", "Area", "Alert / magnitude", "Source"]].fillna("").astype(str)
        filtered = filtered[searchable.apply(lambda col: col.str.casefold().str.contains(term, regex=False)).any(axis=1)]

    map_col, list_col = st.columns([1.5, 1], gap="large")
    with map_col:
        with st.container(border=True):
            st.markdown("### India hazard map")
            mapped = filtered.dropna(subset=["Latitude", "Longitude"]).copy()
            mapped["Latitude"] = pd.to_numeric(mapped["Latitude"], errors="coerce")
            mapped["Longitude"] = pd.to_numeric(mapped["Longitude"], errors="coerce")
            mapped = mapped.dropna(subset=["Latitude", "Longitude"])
            # Keep the map centered on India and show only source records whose
            # coordinates fall within India's approximate geographic bounds.
            mapped = mapped[
                mapped["Latitude"].between(5.0, 38.0)
                & mapped["Longitude"].between(67.0, 98.0)
            ]
            # Bounding boxes also include neighboring countries and offshore areas,
            # so require an India label from the feed before plotting a record.
            india_label = (
                mapped["Area"].fillna("").astype(str).str.contains(r"\bindia\b", case=False, regex=True)
                | mapped["Event"].fillna("").astype(str).str.contains(r"\bindia\b", case=False, regex=True)
            )
            mapped = mapped[india_label].reset_index(drop=True)
            india_glow_layer = pdk.Layer(
                "ScatterplotLayer",
                id="india-incident-glow",
                data=mapped,
                get_position="[Longitude, Latitude]",
                get_fill_color=[255, 170, 0, 58],
                get_radius=105000,
                radius_min_pixels=13,
                radius_max_pixels=28,
                stroked=False,
                pickable=False,
            )
            india_layer = pdk.Layer(
                "ScatterplotLayer",
                id="india-incident-markers",
                data=mapped,
                get_position="[Longitude, Latitude]",
                get_fill_color=[255, 198, 0, 245],
                get_line_color=[255, 255, 255, 255],
                get_radius=50000,
                radius_min_pixels=8,
                radius_max_pixels=18,
                line_width_min_pixels=2,
                pickable=True,
                auto_highlight=True,
            )
            india_view = pdk.ViewState(latitude=22.5, longitude=79.0, zoom=3.5, pitch=0)
            india_deck = pdk.Deck(
                layers=[india_glow_layer, india_layer],
                initial_view_state=india_view,
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={"text": "{Event}\n{Hazard}\n{Area}"},
            )
            map_selection = st.pydeck_chart(
                india_deck,
                use_container_width=True,
                height=460,
                on_select="rerun",
                selection_mode="single-object",
                key="india-incident-map",
            )
            selected_objects = map_selection.selection.get("objects", {}).get("india-incident-markers", [])
            if selected_objects:
                selected_incident = selected_objects[0]
                # Ignore an old selection if the user changes map filters.
                if selected_incident.get("Event") in set(mapped["Event"].astype(str)):
                    with st.container(border=True):
                        st.markdown("#### Selected incident")
                        detail_left, detail_right = st.columns(2)
                        with detail_left:
                            st.write("**Incident:**", selected_incident.get("Event", "Not provided"))
                            st.write("**Hazard:**", selected_incident.get("Hazard", "Not provided"))
                            st.write("**Area:**", selected_incident.get("Area", "Not provided"))
                        with detail_right:
                            st.write("**Alert / magnitude:**", selected_incident.get("Alert / magnitude", "Not reported"))
                            st.write("**Event time (UTC):**", selected_incident.get("Event time (UTC)", "Not provided"))
                            st.write("**Source:**", selected_incident.get("Source", "Not provided"))
                        record_url = str(selected_incident.get("Record") or "")
                        if record_url.startswith(("https://", "http://")):
                            st.link_button("Open source record", record_url)
            st.caption(
                f"{len(mapped)} filtered source events explicitly labeled India and inside India's approximate bounds. "
                "The event stream still includes records from all connected feeds."
            )
    with list_col:
        with st.container(border=True):
            st.markdown(f"### Event stream · {len(filtered)}")
            if filtered.empty:
                st.info("No events match the selected filters.")
            else:
                display = filtered[["Hazard", "Event", "Area", "Alert / magnitude", "Event time (UTC)", "Source", "Record"]]
                st.dataframe(
                    display, use_container_width=True, hide_index=True,
                    column_config={"Record": st.column_config.LinkColumn("Source record", display_text="Verify")},
                    height=520,
                )

    st.markdown("### Coverage and limitations")
    st.caption(
        "GDACS provides multi-hazard global event reporting; USGS provides earthquakes from the past day. "
        "Feed availability and coverage vary by source. Public hazard feeds are not a substitute for official local warnings."
    )
    st.caption(
        "Not connected: live ambulance positions, hospital capacity, shelter occupancy, local dispatch, "
        "verified road closures, or local damage assessments. These are not inferred or filled with fictional records."
    )
