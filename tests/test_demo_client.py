"""Regression tests for the ResQ-AI MCP demo client's argument mapping."""
from argparse import Namespace

from resq_mcp.demo_client import _arguments


def test_incident_list_arguments_are_forwarded():
    args = Namespace(tool="list_incidents", status="resolved", limit=7)
    assert _arguments(args) == {"status": "resolved", "limit": 7}


def test_incident_detail_and_priority_tools_receive_incident_id():
    for tool in ("get_incident_details", "explain_priority"):
        args = Namespace(tool=tool, incident_id="INC-042")
        assert _arguments(args) == {"incident_id": "INC-042"}


def test_shelter_search_receives_minimum_spaces():
    args = Namespace(tool="find_shelters", minimum_spaces=50)
    assert _arguments(args) == {"minimum_spaces": 50}


def test_tools_without_cli_arguments_receive_empty_mapping():
    for tool in (
        "get_resource_status",
        "generate_incident_brief",
        "get_live_government_alerts",
    ):
        assert _arguments(Namespace(tool=tool)) == {}
