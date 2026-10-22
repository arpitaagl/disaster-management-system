"""Unified global hazard monitoring from connected public feeds."""
from __future__ import annotations

from collections import Counter
from html import escape
import re

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from core.gdacs_feed import GDACS_SOURCE_URL, fetch_gdacs_events
from core.live_data import IMD_PUBLIC_CAP_URL, get_imd_live_data, get_ndma_cap_alerts
from core.alert_translation import english_text


@st.cache_data(ttl=300, show_spinner=False)
def _cached_gdacs(lookback_days: int) -> dict:
    return fetch_gdacs_events(lookback_days=lookback_days)


def _is_india_incident(event: dict) -> bool:
    """Keep only explicitly India-located records from global feeds."""
    source = str(event.get("Source") or "")
    if source in {"India Meteorological Department — public CAP", "NDMA SACHET / CAP"}:
        return True

    location_text = f"{event.get('Area') or ''} {event.get('Event') or ''}"
    if not re.search(r"\bindia\b", location_text, flags=re.IGNORECASE):
        return False

    latitude, longitude = event.get("Latitude"), event.get("Longitude")
    if latitude is None or longitude is None:
        return True
    try:
        latitude, longitude = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return False
    return 5.0 <= latitude <= 38.0 and 67.0 <= longitude <= 98.0


_INDIA_STATE_CENTROIDS = {
    "andhra pradesh": (16.5, 80.6), "arunachal pradesh": (28.2, 94.7),
    "assam": (26.2, 92.9), "bihar": (25.9, 85.1), "chhattisgarh": (21.3, 81.8),
    "goa": (15.5, 73.9), "gujarat": (22.3, 71.2), "haryana": (29.0, 76.1),
    "himachal pradesh": (31.1, 77.2), "jharkhand": (23.6, 85.3), "karnataka": (15.3, 75.7),
    "kerala": (10.5, 76.3), "madhya pradesh": (23.5, 78.5), "maharashtra": (19.6, 75.3),
    "manipur": (24.7, 93.9), "meghalaya": (25.5, 91.3), "mizoram": (23.2, 92.7),
    "nagaland": (26.1, 94.6), "odisha": (20.5, 84.4), "orissa": (20.5, 84.4),
    "punjab": (31.1, 75.3), "rajasthan": (26.8, 73.8), "sikkim": (27.5, 88.5),
    "tamil nadu": (11.1, 78.7), "telangana": (18.1, 79.0), "tripura": (23.8, 91.3),
    "uttar pradesh": (26.8, 80.9), "uttarakhand": (30.1, 79.0), "west bengal": (22.9, 87.9),
    "andaman and nicobar": (11.7, 92.7), "chandigarh": (30.7, 76.8),
    "dadra and nagar haveli": (20.2, 73.0), "daman and diu": (20.4, 72.8),
    "delhi": (28.6, 77.2), "jammu and kashmir": (33.7, 76.0), "jammu & kashmir": (33.7, 76.0),
    "ladakh": (34.2, 77.6), "lakshadweep": (10.6, 72.6), "puducherry": (11.9, 79.8),
}


def _approximate_india_coordinates(area: str) -> tuple[float, float] | None:
    """Return a state-level centroid for India alerts whose feed lacks coordinates."""
    location = str(area or "").casefold()
    for state in sorted(_INDIA_STATE_CENTROIDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(state)}\b", location):
            return _INDIA_STATE_CENTROIDS[state]
    return None


def _hazard_name(title: str, summary: str, fallback: str = "Other") -> str:
    """Prefer the hazard described by the alert over its severity rating."""
    text = f"{title} {summary}".casefold()
    hazard_terms = (
        ("Cyclone", ("tropical cyclone", "cyclone", "hurricane", "typhoon")),
        ("Flood", ("flood", "inundat")),
        ("Heavy rainfall", ("heavy rain", "rainfall", "precipitation")),
        ("Storm", ("thunderstorm", "thunder storm", "lightning", "storm", "squall", "gale")),
        ("Heatwave", ("heatwave", "heat wave", "extreme heat")),
        ("Cold / snow", ("cold wave", "coldwave", "cold weather", "snowfall", "heavy snow", "blizzard")),
        ("Landslide", ("landslide", "mudslide")),
        ("Earthquake", ("earthquake", "seismic")),
        ("Drought", ("drought", "dry spell", "water scarcity")),
        ("Wildfire", ("wildfire", "forest fire")),
        ("Tsunami", ("tsunami",)),
    )
    for label, terms in hazard_terms:
        if any(term in text for term in terms):
            return label
    return fallback


def _priority_from_feed(*values: object) -> tuple[str, int]:
    """Normalize official alert severity into a stable ordering for the map."""
    text = " ".join(str(value or "") for value in values).casefold()
    if any(term in text for term in ("extreme", "critical", "very severe", "red")):
        return "Critical", 100
    if any(term in text for term in ("severe", "high", "orange")):
        return "High", 80
    if any(term in text for term in ("moderate", "medium", "yellow")):
        return "Moderate", 60
    if any(term in text for term in ("minor", "low", "green")):
        return "Low", 35
    return "Unrated", 0


def _india_marker_coordinates(area: str, index: int) -> tuple[float, float]:
    """Use a state centroid, or a labeled country-center fallback when location is vague."""
    coordinates = _approximate_india_coordinates(area)
    if coordinates:
        return coordinates
    # Separate otherwise coincident country-level alerts; these are explicitly
    # labeled as approximate and do not claim to be event coordinates.
    offsets = ((0.0, 0.0), (0.34, 0.0), (-0.34, 0.0), (0.0, 0.42), (0.0, -0.42),
               (0.34, 0.42), (-0.34, 0.42), (0.34, -0.42), (-0.34, -0.42))
    lat_offset, lon_offset = offsets[index % len(offsets)]
    return 22.5 + lat_offset, 79.0 + lon_offset


def _select_stream_events(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Show the highest-priority matching India incidents first."""
    hazard_order = {
        name: index for index, name in enumerate((
            "Flood", "Drought", "Landslide", "Earthquake", "Cyclone", "Heavy rainfall",
            "Storm", "Heatwave", "Cold / snow", "Wildfire", "Other",
        ))
    }
    ranked = frame.assign(
        _hazard_order=frame["Hazard"].map(hazard_order).fillna(len(hazard_order))
    ).sort_values(
        ["Priority score", "_hazard_order"], ascending=[False, True], kind="stable"
    )
    return ranked.head(limit).drop(columns="_hazard_order")


@st.fragment(run_every=300)
def render_live_disaster_intelligence() -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / GLOBAL MONITORING</div>', unsafe_allow_html=True)
    st.title("Live Disaster Intelligence")
    st.caption(
        "India-focused incidents from GDACS, IMD public CAP, and NDMA SACHET when their feeds provide India location details. "
        "These public feeds do not confirm local damage, casualties, or dispatch requirements."
    )

    with st.container(border=True, key="live-feed-controls"):
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
                    "Hazard": _hazard_name(
                        f"{event.get('event_type', '')} {event.get('name', '')}",
                        event.get("alert_level", ""),
                    ),
                    "Event": event.get("name", "Name not provided"),
                    "Area": event.get("country", "Not provided"),
                    "Alert / magnitude": event.get("alert_level", "Not reported"),
                    "Event time (UTC)": event.get("started_at_utc") or "Not provided",
                    "Source": "GDACS",
                    "Record": event.get("source_url") or GDACS_SOURCE_URL,
                    "Latitude": event.get("latitude"),
                    "Longitude": event.get("longitude"),
                    "Priority": _priority_from_feed(event.get("alert_level"))[0],
                    "Priority score": _priority_from_feed(event.get("alert_level"))[1],
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            failures.append(("GDACS", type(exc).__name__, GDACS_SOURCE_URL))
            source_rows.append({
                "Source": "GDACS", "Status": "Unavailable", "Events": "—",
                "Retrieved by app (UTC)": "—", "Latest event update/start (UTC)": "—", "Official source": GDACS_SOURCE_URL,
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
        for alert_index, row in enumerate(imd_alerts):
            title = english_text(row.get("title", ""))
            if not title:
                continue
            summary = english_text(row.get("summary", ""))
            area = english_text(row.get("area", ""))
            events.append({
                "Hazard": _hazard_name(title, summary),
                "Event": title,
                "Area": area or "Location not provided",
                "Alert / magnitude": summary or "See official alert",
                "Event time (UTC)": row.get("published") or "Not provided",
                "Source": "India Meteorological Department — public CAP",
                "Record": row.get("link") or public_result.get("source_url") or IMD_PUBLIC_CAP_URL,
                "Latitude": _india_marker_coordinates(area, alert_index)[0],
                "Longitude": _india_marker_coordinates(area, alert_index)[1],
                "Priority": _priority_from_feed(row.get("severity"))[0],
                "Priority score": _priority_from_feed(row.get("severity"))[1],
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
        for alert_index, row in enumerate(ndma_alerts):
            title = english_text(row.get("title", ""))
            if not title:
                continue
            summary = english_text(row.get("summary", ""))
            area = english_text(row.get("area", ""))
            events.append({
                "Hazard": _hazard_name(title, summary),
                "Event": title,
                "Area": area or "Location not provided",
                "Alert / magnitude": summary or "See official alert",
                "Event time (UTC)": row.get("published") or "Not provided",
                "Source": "NDMA SACHET / CAP",
                "Record": row.get("link") or ndma.get("source_url") or "https://sachet.ndma.gov.in/",
                "Latitude": _india_marker_coordinates(area, alert_index)[0],
                "Longitude": _india_marker_coordinates(area, alert_index)[1],
                "Priority": _priority_from_feed(row.get("severity"))[0],
                "Priority score": _priority_from_feed(row.get("severity"))[1],
            })
    except (requests.RequestException, ValueError, TypeError):
        source_rows.append({
            "Source": "NDMA SACHET / CAP", "Status": "Unavailable", "Events": "—",
            "Retrieved by app (UTC)": "—", "Latest event update/start (UTC)": "—",
            "Official source": "https://sachet.ndma.gov.in/",
        })

    events = [event for event in events if _is_india_incident(event)]
    india_only_sources = {
        "India Meteorological Department — public CAP", "NDMA SACHET / CAP"
    }
    for marker_index, event in enumerate(events):
        approximate = event.get("Source") in india_only_sources
        try:
            latitude, longitude = float(event.get("Latitude")), float(event.get("Longitude"))
        except (TypeError, ValueError):
            latitude, longitude = None, None
        if latitude is None or longitude is None:
            latitude, longitude = _india_marker_coordinates(str(event.get("Area") or ""), marker_index)
            approximate = True
        event["Latitude"] = latitude
        event["Longitude"] = longitude
        event["Location approximate"] = approximate
    india_counts = Counter(event["Source"] for event in events)
    india_health_rows = []
    for source_row in source_rows:
        source_name = source_row["Source"]
        india_incidents = (
            india_counts.get(source_name, 0)
            if source_row["Status"] == "Connected"
            else "—"
        )
        source_row.pop("Events", None)
        india_health_rows.append({
            "Source": source_name,
            "Status": source_row.pop("Status"),
            "India incidents": india_incidents,
            **source_row,
        })
    source_rows = india_health_rows

    connected = sum(row["Status"] == "Connected" for row in source_rows)
    with st.container(key="india-incident-metrics"):
        c1, c2, c3 = st.columns(3)
        c1.metric("India incidents", len(events))
        c2.metric("Feeds connected", f"{connected} / {len(source_rows)}")
        c3.metric("Monitoring window", f"Past {lookback} days")

    with st.expander("Data-source health", expanded=bool(failures) or force_refresh):
        health_df = pd.DataFrame(source_rows)
        health_columns = [
            "Source", "Status", "India incidents", "Retrieved by app (UTC)",
            "Latest event update/start (UTC)", "Source feed generated (UTC)", "Official source",
        ]
        health_df = health_df[[column for column in health_columns if column in health_df.columns]]
        st.dataframe(
            health_df, use_container_width=True, hide_index=True, column_order=health_df.columns.tolist(),
            column_config={
                "Source": st.column_config.TextColumn("Source", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "India incidents": st.column_config.TextColumn("India incidents", width="small"),
                "Official source": st.column_config.LinkColumn("Official source", display_text="Open source"),
            },
        )
        for name, reason, url in failures:
            st.warning(f"{name} is unavailable ({reason}). No example events were substituted. [Open official source]({url})")
        st.caption(
            "India incident counts include only records explicitly located in India. App retrieval time means when this app received the response; it does not mean every event is new. "
            "GDACS may continue listing ongoing alerts."
        )
        if force_refresh:
            st.success("Refresh requested: GDACS was fetched directly, bypassing the five-minute cache.")
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
    hazard_categories = [
        "Flood", "Drought", "Earthquake", "Cyclone", "Heavy rainfall",
        "Storm", "Heatwave", "Cold / snow", "Wildfire", "Landslide", "Other",
    ]
    f1, f2, f3 = st.columns([1, 1, 2])
    with f1:
        hazard_options = ["All hazards"] + hazard_categories
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
    search_terms = [
        term.casefold()
        for term in (query.strip(), str(st.session_state.get("resq_global_search") or "").strip())
        if term
    ]
    for term in search_terms:
        searchable = filtered[["Hazard", "Event", "Area", "Alert / magnitude", "Source"]].fillna("").astype(str)
        filtered = filtered[searchable.apply(lambda col: col.str.casefold().str.contains(term, regex=False)).any(axis=1)]

    matching_count = len(filtered)
    filtered = _select_stream_events(filtered, limit=10)
    map_events = filtered.head(8).copy()

    map_col, list_col = st.columns([2, 1], gap="large")
    with map_col:
        with st.container(border=True):
            st.markdown("### India hazard map")
            mapped = map_events.dropna(subset=["Latitude", "Longitude"]).copy()
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
                | mapped["Source"].isin({"India Meteorological Department — public CAP", "NDMA SACHET / CAP"})
            )
            mapped = mapped[india_label].reset_index(drop=True)
            mapped["tooltip_event"] = mapped["Event"].fillna("Incident").astype(str).map(escape)
            mapped["tooltip_hazard"] = mapped["Hazard"].fillna("Other").astype(str).map(escape)
            mapped["tooltip_priority"] = mapped["Priority"].fillna("Unrated").astype(str).map(escape)
            mapped["tooltip_description"] = (
                mapped["Alert / magnitude"].fillna("No short description provided")
                .astype(str).str.replace(r"\s+", " ", regex=True).str.slice(0, 180).map(escape)
            )
            mapped["tooltip_location"] = mapped["Area"].fillna("Location not provided").astype(str).map(escape)
            mapped.loc[mapped["Location approximate"], "tooltip_location"] += " (approximate marker)"
            # Keep the marker palette consistent between the map and its legend.
            hazard_palette = [
                ("Flood", "#ef4444", [239, 68, 68, 245], ("flood", "inundat")),
                ("Drought", "#eab308", [234, 179, 8, 245], ("drought", "dry spell", "water scarcity")),
                ("Earthquake", "#8b5cf6", [139, 92, 246, 245], ("earthquake", "seismic")),
                ("Cyclone", "#06b6d4", [6, 182, 212, 245], ("cyclone", "hurricane", "typhoon")),
                ("Heavy rainfall", "#2563eb", [37, 99, 235, 245], ("heavy rainfall", "heavy rain", "rainfall", "precipitation")),
                ("Storm", "#4f46e5", [79, 70, 229, 245], ("storm", "thunder", "lightning")),
                ("Heatwave", "#f59e0b", [245, 158, 11, 245], ("heatwave", "heat wave", "extreme heat")),
                ("Cold / snow", "#38bdf8", [56, 189, 248, 245], ("cold wave", "coldwave", "snowfall", "heavy snow", "blizzard")),
                ("Wildfire", "#f97316", [249, 115, 22, 245], ("wildfire", "forest fire")),
                ("Landslide", "#22c55e", [34, 197, 94, 245], ("landslide", "mudslide")),
                ("Other", "#ec4899", [236, 72, 153, 245], ()),
            ]

            def marker_color(event):
                hazard = str(event.get("Hazard") or "Other")
                for label, _, rgba, _ in hazard_palette:
                    if hazard == label:
                        return rgba
                return hazard_palette[-1][2]

            mapped["Marker color"] = mapped.apply(marker_color, axis=1)
            # Use numeric accessor fields instead of a list-valued dataframe column;
            # map each channel independently so empty source results stay valid too.
            mapped["marker_r"] = mapped["Marker color"].map(lambda color: color[0])
            mapped["marker_g"] = mapped["Marker color"].map(lambda color: color[1])
            mapped["marker_b"] = mapped["Marker color"].map(lambda color: color[2])
            mapped["core_r"] = (mapped["marker_r"] * 0.62).astype(int)
            mapped["core_g"] = (mapped["marker_g"] * 0.62).astype(int)
            mapped["core_b"] = (mapped["marker_b"] * 0.62).astype(int)
            legend_items = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:.38rem;margin:0 .8rem .4rem 0;white-space:nowrap;">'
                f'<i style="width:.72rem;height:.72rem;border-radius:50%;background:{color};box-shadow:0 0 9px {color};display:inline-block;"></i>{label}</span>'
                for label, color, _, _ in hazard_palette
            )
            st.markdown(
                f'<div style="font-size:.82rem;line-height:1.8;padding:.15rem 0 .35rem;">{legend_items}</div>',
                unsafe_allow_html=True,
            )
            india_glow_layer = pdk.Layer(
                "ScatterplotLayer",
                id="india-incident-outer-glow",
                data=mapped,
                get_position="[Longitude, Latitude]",
                get_fill_color="[marker_r, marker_g, marker_b, 48]",
                get_radius=36000,
                radius_min_pixels=4,
                radius_max_pixels=8,
                stroked=False,
                pickable=False,
            )
            india_bloom_layer = pdk.Layer(
                "ScatterplotLayer",
                id="india-incident-bloom",
                data=mapped,
                get_position="[Longitude, Latitude]",
                get_fill_color="[marker_r, marker_g, marker_b, 130]",
                get_radius=18000,
                radius_min_pixels=2,
                radius_max_pixels=4,
                stroked=False,
                pickable=False,
            )
            india_layer = pdk.Layer(
                "ScatterplotLayer",
                id="india-incident-markers",
                data=mapped,
                get_position="[Longitude, Latitude]",
                get_fill_color="[marker_r, marker_g, marker_b, 255]",
                get_line_color=[255, 255, 255, 245],
                get_radius=9000,
                radius_min_pixels=2,
                radius_max_pixels=3,
                line_width_min_pixels=1,
                pickable=True,
                auto_highlight=True,
            )
            india_view = pdk.ViewState(latitude=22.5, longitude=79.0, zoom=3.5, pitch=0)
            india_deck = pdk.Deck(
                layers=[india_glow_layer, india_bloom_layer, india_layer],
                initial_view_state=india_view,
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={
                    "html": "<div style='max-width:280px;line-height:1.45'>"
                    "<strong>{tooltip_event}</strong><br/>"
                    "<b>Priority:</b> {tooltip_priority} · <b>Hazard:</b> {tooltip_hazard}<br/>"
                    "<b>Location:</b> {tooltip_location}<br/>"
                    "{tooltip_description}</div>",
                    "style": {
                        "backgroundColor": "#10253d",
                        "color": "#f5fbff",
                        "border": "1px solid #41cde0",
                        "borderRadius": "10px",
                        "padding": "10px 12px",
                        "fontSize": "12px",
                    },
                },
            )
            map_selection = st.pydeck_chart(
                india_deck,
                use_container_width=True,
                height=560,
                on_select="rerun",
                selection_mode="single-object",
                key="india-incident-map",
            )
            selection = map_selection.selection
            selected_objects = selection.get("objects", {}).get("india-incident-markers", [])
            if not selected_objects:
                selected_indices = selection.get("indices", {}).get("india-incident-markers", [])
                if selected_indices:
                    selected_index = selected_indices[0]
                    if 0 <= selected_index < len(mapped):
                        selected_objects = [mapped.iloc[selected_index].to_dict()]
            if selected_objects:
                selected_incident = selected_objects[0]
                # Ignore an old selection if the user changes map filters.
                if selected_incident.get("Event") in set(mapped["Event"].astype(str)):
                    with st.container(border=True):
                        st.markdown("#### Selected incident details")
                        st.write("**Incident:**", selected_incident.get("Event", "Not provided"))
                        st.write("**Priority:**", selected_incident.get("Priority", "Unrated"))
                        st.write("**Hazard:**", selected_incident.get("Hazard", "Other"))
                        lat = float(selected_incident.get("Latitude"))
                        lon = float(selected_incident.get("Longitude"))
                        approximate = bool(selected_incident.get("Location approximate", False))
                        location_text = str(selected_incident.get("Area") or "India")
                        precision_note = " · approximate marker; feed did not provide precise coordinates" if approximate else ""
                        st.write("**Location:**", f"{location_text} ({lat:.3f}, {lon:.3f}){precision_note}")
                        description = str(selected_incident.get("Alert / magnitude") or "No short description provided")
                        description = " ".join(description.split())
                        if len(description) > 280:
                            description = description[:277].rsplit(" ", 1)[0] + "..."
                        st.write("**Description:**", description)
                        st.write("**Time (UTC):**", selected_incident.get("Event time (UTC)", "Time not provided"))
                        st.write("**Source:**", selected_incident.get("Source", "Source not provided"))
                        record_url = str(selected_incident.get("Record") or "")
                        if record_url.startswith(("https://", "http://")):
                            st.link_button("Open source record", record_url)
            st.caption(
                f"Map shows the first {len(mapped)} of {len(filtered)} priority-ranked incidents in the event stream. "
                "Government alerts without coordinates use an approximate state or India-level marker, labeled as approximate when selected. Only India-located records are shown in the event stream."
            )
    with list_col:
        with st.container(border=True):
            st.markdown(f"### Event stream · {len(filtered)}")
            if matching_count > len(filtered):
                st.caption(f"Showing the 10 highest-priority of {matching_count} matching India source events. The map starts with the first 8.")
            if filtered.empty:
                st.info("No events match the selected filters.")
            else:
                display = filtered[["Priority", "Hazard", "Event", "Area", "Alert / magnitude", "Event time (UTC)", "Source", "Record"]]
                st.dataframe(
                    display, use_container_width=True, hide_index=True,
                    column_config={"Record": st.column_config.LinkColumn("Source record", display_text="Verify")},
                    height=520,
                )

    st.markdown("### Coverage and limitations")
    st.caption(
        "GDACS provides multi-hazard event reporting. "
        "Feed availability and coverage vary by source. Public hazard feeds are not a substitute for official local warnings."
    )
    st.caption(
        "Not connected: live ambulance positions, hospital capacity, shelter occupancy, local dispatch, "
        "verified road closures, or local damage assessments. These are not inferred or filled with fictional records."
    )
