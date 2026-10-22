"""Read-only MCP server for Alexa+ and compatible MCP clients."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from resq_mcp.auth import auth_configuration

from core.state import load_demo_disaster
from core.live_data import get_imd_live_data, get_ndma_cap_alerts
from resq_mcp.logic import (
    explain_priority as _explain_priority,
    find_shelters as _find_shelters,
    generate_incident_brief as _generate_incident_brief,
    get_incident_details as _get_incident_details,
    get_resource_status as _get_resource_status,
    list_incidents as _list_incidents,
)

_auth_config = auth_configuration()

mcp = FastMCP(
    "ResQ-AI Disaster Response",
    instructions=(
        "Read-only disaster-response decision support. Use tools to inspect the supplied ResQ-AI "
        "demo state, explain deterministic priority scores, and summarize reported capacity. "
        "Never claim the demo data is live. Never authorize dispatch or replace emergency authorities."
    ),
    # Render's proxy requires 0.0.0.0 and its injected PORT. Keep local overrides available.
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", os.getenv("MCP_PORT", "8000"))),
    stateless_http=True,
    json_response=True,
    token_verifier=_auth_config[0] if _auth_config else None,
    auth=_auth_config[1] if _auth_config else None,
)


@lru_cache(maxsize=1)
def _center() -> Any:
    """Load one prepared simulated flood scenario for this MCP server process."""
    return load_demo_disaster()


@mcp.tool()
def list_incidents(status: str = "active", limit: int = 10) -> dict[str, Any]:
    """List current demo incidents by deterministic priority, highest first."""
    return _list_incidents(_center(), status=status, limit=limit)


@mcp.tool()
def get_incident_details(incident_id: str) -> dict[str, Any]:
    """Get one incident's summary, status, recommendation, and score breakdown."""
    return _get_incident_details(_center(), incident_id)


@mcp.tool()
def explain_priority(incident_id: str) -> dict[str, Any]:
    """Explain an incident's existing deterministic priority score and component breakdown."""
    return _explain_priority(_center(), incident_id)


@mcp.tool()
def get_resource_status() -> dict[str, Any]:
    """Report rescue-team availability, hospital beds, and shelter capacity in the demo state."""
    return _get_resource_status(_center())


@mcp.tool()
def find_shelters(minimum_spaces: int = 0) -> dict[str, Any]:
    """Find shelters with at least this many reported free spaces; capacity must be verified."""
    return _find_shelters(_center(), minimum_spaces=minimum_spaces)


@mcp.tool()
def generate_incident_brief() -> dict[str, Any]:
    """Generate a concise response brief, using Amazon Bedrock Converse when configured."""
    return _generate_incident_brief(_center())


@mcp.tool()
def get_live_government_alerts(state: str = "", district: str = "") -> dict[str, Any]:
    """Fetch current IMD district nowcasts/warnings and the configured official NDMA SACHET/CAP feed.

    Results are source-attributed and may be unavailable without authorized feed credentials.
    Alerts are not verified incidents and this read-only tool never changes priority scores or dispatches resources.
    """
    imd = get_imd_live_data(state=state, district=district)
    ndma = get_ndma_cap_alerts()
    return {
        "data_mode": "live_government_sources",
        "checked_at": imd.get("fetched_at") or ndma.get("fetched_at"),
        "imd": imd,
        "ndma": ndma,
        "note": "Government hazard alerts are not confirmed rescue incidents. Verify the source and local impact; no scores or assignments are changed.",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
