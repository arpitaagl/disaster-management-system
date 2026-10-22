from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_component = components.declare_component(
    "resq_google_location_picker",
    path=str(Path(__file__).with_name("google_location_picker_frontend")),
)


def google_location_picker(*, api_key: str, default_lat: float, default_lon: float, key: str):
    """Render a Google Maps picker and return {lat, lon, address} after selection."""
    return _component(
        apiKey=api_key,
        defaultLat=float(default_lat),
        defaultLng=float(default_lon),
        key=key,
        default=None,
    )
