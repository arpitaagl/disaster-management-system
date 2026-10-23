"""Nearby rescue-related public directory lookup without Overpass or HTML scraping."""
from __future__ import annotations

import math
from typing import Any

import requests
import streamlit as st

PHOTON_URL = "https://photon.komoot.io/api/"


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1.0 - value)))


@st.cache_data(ttl=900, show_spinner=False)
def nearby_rescue_listings(lat: Any, lon: Any, limit: int = 7) -> tuple[list[dict[str, Any]], str | None]:
    """Return geocoded rescue/NDRF/SDRF public listings near saved incident coordinates.

    Photon is a place-search endpoint; this intentionally does not use Overpass
    interpreter queries or scrape the NDRF HTML table. Listings are directory leads,
    not confirmation of live crew location or availability.
    """
    try:
        incident_lat, incident_lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return [], "Incident coordinates are missing or invalid."
    if not (-90 <= incident_lat <= 90 and -180 <= incident_lon <= 180):
        return [], "Incident coordinates are outside valid latitude/longitude ranges."

    headers = {"User-Agent": "ResQ-AI public rescue directory/1.0"}
    searches = (
        "NDRF", "SDRF rescue", "rescue station", "rescue service",
        "disaster response force", "civil defence rescue",
    )
    found: dict[str, dict[str, Any]] = {}
    failures = 0
    for query in searches:
        try:
            response = requests.get(
                PHOTON_URL,
                params={"q": query, "lat": incident_lat, "lon": incident_lon, "limit": 10, "lang": "en"},
                headers=headers,
                timeout=(3, 7),
            )
            response.raise_for_status()
            features = response.json().get("features") or []
        except (requests.RequestException, ValueError, TypeError):
            failures += 1
            continue

        for feature in features:
            props = feature.get("properties") or {}
            coords = (feature.get("geometry") or {}).get("coordinates") or []
            if len(coords) < 2:
                continue
            try:
                item_lon, item_lat = float(coords[0]), float(coords[1])
                distance = _distance_km(incident_lat, incident_lon, item_lat, item_lon)
            except (TypeError, ValueError):
                continue
            if distance > 50:
                continue

            name = str(props.get("name") or props.get("street") or "").strip()
            if not name:
                continue
            searchable = " ".join(str(props.get(k) or "") for k in ("name", "type", "subtype", "osm_key", "osm_value", "city", "district"))
            if not any(term in searchable.casefold() for term in (
                "rescue", "ndrf", "sdrf", "disaster response", "civil defence", "civil defense",
            )):
                continue

            osm_id = str(props.get("osm_id") or "")
            osm_type = str(props.get("osm_type") or "N")
            key = osm_id or f"{name.casefold()}:{item_lat:.5f}:{item_lon:.5f}"
            parts = [
                str(props.get("housenumber") or "").strip(),
                str(props.get("street") or "").strip(),
                str(props.get("district") or "").strip(),
                str(props.get("city") or props.get("county") or "").strip(),
                str(props.get("state") or "").strip(),
            ]
            address = ", ".join(dict.fromkeys(p for p in parts if p))
            found[key] = {
                "name": name,
                "type": "Rescue / disaster-response listing",
                "distance_km": round(distance, 1),
                "phone": str(props.get("phone") or "").strip(),
                "address": address,
                "website": str(props.get("website") or "").strip(),
                "source": "Photon public place directory",
                "source_url": f"https://www.openstreetmap.org/{osm_type.lower()}/{osm_id}" if osm_id else "https://photon.komoot.io/",
                "lat": item_lat,
                "lon": item_lon,
            }

    results = sorted(found.values(), key=lambda row: row["distance_km"])[:max(0, min(int(limit), 7))]
    if results:
        return results, None
    if failures == len(searches):
        return [], "The public rescue-place directory could not be reached right now."
    return [], None
