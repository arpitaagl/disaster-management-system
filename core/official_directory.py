"""Public hospital reference lookup; this is not a live bed/dispatch feed."""
from __future__ import annotations

import math
from typing import Any

import requests
import streamlit as st

from core.geo import haversine_km

HOSPITAL_LAYER_QUERY = (
    "https://livingatlas.esri.in/server/rest/services/"
    "LivingAtlas/IND_Hospital_Directory/MapServer/0/query"
)
SOURCE_URL = (
    "https://livingatlas.esri.in/server/rest/services/"
    "LivingAtlas/IND_Hospital_Directory/MapServer/0"
)


@st.cache_data(ttl=1800, show_spinner=False)
def _query_hospitals(lat: float, lon: float) -> list[dict[str, Any]]:
    """Fetch public facility reference records near a reported incident."""
    params = {
        "f": "json",
        "where": "1=1",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": "50000",
        "units": "esriSRUnit_Meter",
        "outFields": "objectid,health_facility_name,address,locality,posatalcode,landline_number,facility_type,state_name,district_name,lat,lon",
        "returnGeometry": "false",
        "outSR": "4326",
        "resultRecordCount": 1000,
        "orderByFields": "health_facility_name",
    }
    response = requests.get(HOSPITAL_LAYER_QUERY, params=params, timeout=12)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError("The public hospital directory returned an API error.")
    rows = []
    for feature in payload.get("features") or []:
        attrs = feature.get("attributes") or {}
        try:
            hlat, hlon = float(attrs.get("lat")), float(attrs.get("lon"))
        except (TypeError, ValueError):
            continue
        if not (-90 <= hlat <= 90 and -180 <= hlon <= 180):
            continue
        distance = haversine_km(lat, lon, hlat, hlon)
        if not math.isfinite(distance) or distance > 50:
            continue
        name = str(attrs.get("health_facility_name") or "").strip()
        if not name:
            continue
        oid = attrs.get("objectid")
        rows.append({
            "id": f"PUBLIC-HOSP-{oid}",
            "name": name,
            "lat": hlat,
            "lon": hlon,
            "address": ", ".join(dict.fromkeys(
                part for part in [
                    str(attrs.get("address") or "").strip(),
                    str(attrs.get("locality") or "").strip(),
                    str(attrs.get("posatalcode") or "").strip(),
                ] if part
            )),
            "district": str(attrs.get("district_name") or "").strip(),
            "state": str(attrs.get("state_name") or "").strip(),
            "phone": str(attrs.get("landline_number") or "").strip(),
            "facility_type": str(attrs.get("facility_type") or "Health facility").strip(),
            "source": SOURCE_URL,
            "source_type": "public_reference_directory",
            "availability_status": "unknown",
            "available_beds": 0,
            "emergency_capability": None,
            "distance_km": round(distance, 2),
        })
    return sorted(rows, key=lambda item: item["distance_km"])


def nearby_public_hospitals(lat: Any, lon: Any, limit: int = 10) -> tuple[list[dict[str, Any]], str | None]:
    """Return nearby directory entries and a safe error message, if unavailable."""
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return [], "Incident coordinates are missing or invalid; nearby hospitals cannot be searched."
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return [], "Incident coordinates are outside valid latitude/longitude ranges."
    try:
        return _query_hospitals(round(lat_f, 5), round(lon_f, 5))[:limit], None
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        return [], f"Public hospital directory is temporarily unavailable ({type(exc).__name__})."


def nearby_major_hospitals(lat: Any, lon: Any, limit: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    """Return the nearest named hospital-level facilities, including records without phones.

    Nearby hospitals must not be hidden just because the reference directory lacks a
    phone number. Results are distance-sorted; facilities within 2 km naturally appear
    first, with farther facilities used as fallback when fewer results are available.
    The source is a public reference directory, not a live contact or availability feed.
    """
    records, error = nearby_public_hospitals(lat, lon, limit=1000)
    if error:
        return [], error

    excluded = (
        "subcentre", "sub center", "sub-centre", "primary health centre",
        "primary health center", "dispensary", "clinic", "urban health centre",
        "urban health center", "health sub-centre", "health sub center",
        "anganwadi", "wellness centre", "wellness center",
    )
    major_terms = (
        "hospital", "medical college", "aiims", "institute of medical sciences",
        "super speciality", "super specialty", "tertiary care",
    )
    selected = []
    seen = set()
    for record in records:
        name = str(record.get("name") or "").strip()
        phone = str(record.get("phone") or "").strip()
        facility_type = str(record.get("facility_type") or "").strip()
        name_key, type_key = name.casefold(), facility_type.casefold()
        if not name or any(term in type_key for term in excluded):
            continue
        if not (any(term in type_key for term in major_terms) or any(term in name_key for term in major_terms)):
            continue
        key = (name_key, str(record.get("address") or "").casefold())
        if key in seen:
            continue
        seen.add(key)
        selected.append(record)
    return selected[:max(0, min(int(limit), 5))], None
