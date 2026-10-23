"""Public hospital reference lookup; this is not a live bed/dispatch feed."""
from __future__ import annotations

import math
from io import StringIO
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
    """Return named hospital-level facilities with a directory-listed phone number.

    The source is a public reference directory, not an official live contact registry.
    A listed number must never be described as independently verified by ResQ-AI.
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
        address = str(record.get("address") or "").strip()
        district = str(record.get("district") or "").strip()
        state = str(record.get("state") or "").strip()
        name_key, type_key = name.casefold(), facility_type.casefold()

        # Only show actionable directory entries: a real-looking listed phone
        # number and a sufficiently complete address. Never fill missing fields
        # with guessed contact details.
        digits = "".join(character for character in phone if character.isdigit())
        placeholder_phone = phone.casefold() in {
            "", "n/a", "na", "not available", "not listed", "none", "null", "nan", "-"
        }
        if not name or placeholder_phone or len(digits) < 7:
            continue
        if not address or not state:
            continue
        if any(term in type_key for term in excluded):
            continue
        if not (
            any(term in type_key for term in major_terms)
            or any(term in name_key for term in major_terms)
        ):
            continue

        key = name_key
        if key in seen:
            continue
        seen.add(key)
        selected.append(record)
    return selected[:max(0, min(int(limit), 5))], None



NDRF_UNITS_URL = "https://www.ndrf.gov.in/ndrf-units"


@st.cache_data(ttl=86400, show_spinner=False)
def _geocode_ndrf_address(address: str) -> tuple[float, float] | None:
    """Geocode an address published in the official NDRF unit directory."""
    if not address.strip():
        return None
    headers = {"User-Agent": "ResQ-AI public directory lookup/1.0"}
    try:
        response = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": address, "limit": 1},
            headers=headers,
            timeout=(3, 8),
        )
        response.raise_for_status()
        features = response.json().get("features") or []
        if features:
            coords = features[0].get("geometry", {}).get("coordinates") or []
            if len(coords) >= 2:
                lon_f, lat_f = float(coords[0]), float(coords[1])
                if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
                    return lat_f, lon_f
    except (requests.RequestException, ValueError, TypeError, IndexError):
        return None
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_official_ndrf_units() -> tuple[list[dict[str, Any]], str | None]:
    """Read unit contacts from NDRF's official public website; not live deployment status."""
    import pandas as pd

    try:
        response = requests.get(
            NDRF_UNITS_URL,
            headers={"User-Agent": "ResQ-AI official public directory reader/1.0"},
            timeout=(4, 12),
        )
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
    except (requests.RequestException, ValueError, ImportError, OSError) as exc:
        return [], f"Official NDRF directory is temporarily unavailable ({type(exc).__name__})."

    records: list[dict[str, Any]] = []
    for table in tables:
        table.columns = [str(col).strip().casefold() for col in table.columns]
        unit_col = next((col for col in table.columns if "unit" in col or "battalion" in col), None)
        address_col = next((col for col in table.columns if "address" in col), None)
        phone_col = next((col for col in table.columns if "telephone" in col or "phone" in col), None)
        control_col = next((col for col in table.columns if "control room" in col), None)
        email_col = next((col for col in table.columns if "e-mail" in col or "email" in col), None)
        if not unit_col or not address_col:
            continue
        for _, row in table.iterrows():
            name = str(row.get(unit_col, "")).strip()
            address = str(row.get(address_col, "")).strip()
            if not name or name.casefold() in {"nan", "unit", "battalion"} or not address or address.casefold() == "nan":
                continue
            phone = str(row.get(phone_col, "")).strip() if phone_col else ""
            control = str(row.get(control_col, "")).strip() if control_col else ""
            email = str(row.get(email_col, "")).strip() if email_col else ""
            records.append({
                "name": name,
                "address": address,
                "phone": "" if phone.casefold() == "nan" else phone,
                "control_room": "" if control.casefold() == "nan" else control,
                "email": "" if email.casefold() == "nan" else email,
                "source_url": NDRF_UNITS_URL,
            })
    # De-duplicate tables/rows that some CMS pages expose more than once.
    deduped = {}
    for record in records:
        deduped[record["name"].casefold()] = record
    if not deduped:
        return [], "The official NDRF page loaded, but its unit table format was not recognized."
    return list(deduped.values()), None


@st.cache_data(ttl=3600, show_spinner=False)
def nearby_official_ndrf_units(lat: Any, lon: Any, limit: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    """Return nearest geocoded NDRF headquarters from its official public unit directory.

    The source confirms public unit contact/address details only; it does not expose
    live team position, readiness, or dispatch availability.
    """
    try:
        incident_lat, incident_lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return [], "Incident coordinates are missing or invalid; NDRF units cannot be ranked."
    if not (-90 <= incident_lat <= 90 and -180 <= incident_lon <= 180):
        return [], "Incident coordinates are outside valid latitude/longitude ranges."
    records, error = _fetch_official_ndrf_units()
    if error:
        return [], error
    nearby = []
    for record in records:
        coords = _geocode_ndrf_address(record["address"])
        if not coords:
            continue
        unit_lat, unit_lon = coords
        distance = haversine_km(incident_lat, incident_lon, unit_lat, unit_lon)
        nearby.append({
            **record,
            "lat": unit_lat,
            "lon": unit_lon,
            "distance_km": round(distance, 1),
            "type": "Official NDRF unit directory",
            "source": "Official NDRF public website",
        })
    nearby.sort(key=lambda item: item["distance_km"])
    return nearby[:max(0, min(int(limit), 10))], None
