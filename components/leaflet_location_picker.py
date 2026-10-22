from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component(
    "resq_leaflet_location_picker",
    path=str(Path(__file__).with_name("leaflet_location_picker_frontend")),
)


def leaflet_location_picker(*, default_lat: float, default_lon: float, key: str):
    """Render an OpenStreetMap/Leaflet picker and return {lat, lon, address}."""
    return _component(
        defaultLat=float(default_lat),
        defaultLng=float(default_lon),
        key=key,
        default=None,
    )
