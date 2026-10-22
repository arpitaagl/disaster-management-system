"""Tests for the optional Amazon Bedrock incident-briefing integration.

These tests mock the AWS SDK. They validate the integration contract without
requiring AWS credentials or making billable network requests.
"""
import sys
import types

from resq_mcp.logic import generate_incident_brief


class FakeCenter:
    demo_mode = True
    incidents = [
        {
            "id": "INC-001",
            "disaster_type": "Flood",
            "priority_score": 91,
            "urgency": "Critical",
            "status": "Active",
            "people_affected": 70,
            "recommended_action": "Prioritize medical-capable response",
        }
    ]

    def metrics(self):
        return {
            "active_incidents": 1,
            "critical_incidents": 1,
            "people_affected": 70,
            "available_resources": 1,
            "hospital_beds_available": 4,
            "shelter_spaces_available": 25,
        }


def test_bedrock_briefing_uses_configured_model_and_region(monkeypatch):
    calls = {}

    class FakeRuntimeClient:
        def converse(self, **kwargs):
            calls.update(kwargs)
            return {
                "output": {
                    "message": {
                        "content": [{"text": "Coordinator briefing: verify the school-flood report."}]
                    }
                }
            }

    fake_boto3 = types.SimpleNamespace(
        client=lambda service, region_name: (
            calls.update({"service": service, "region_name": region_name})
            or FakeRuntimeClient()
        )
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("AWS_BEDROCK_MODEL_ID", "test-model-id")
    monkeypatch.setenv("AWS_REGION", "ap-south-1")

    result = generate_incident_brief(FakeCenter())

    assert result["mode"] == "amazon_bedrock"
    assert result["model_id"] == "test-model-id"
    assert "verify the school-flood report" in result["brief"]
    assert calls["service"] == "bedrock-runtime"
    assert calls["region_name"] == "ap-south-1"
    assert calls["modelId"] == "test-model-id"
    assert "simulated data" in calls["system"][0]["text"]
    assert calls["inferenceConfig"]["maxTokens"] == 500


def test_bedrock_failure_returns_safe_deterministic_fallback(monkeypatch):
    class FailingRuntimeClient:
        def converse(self, **kwargs):
            raise RuntimeError("simulated service outage")

    fake_boto3 = types.SimpleNamespace(
        client=lambda service, region_name: FailingRuntimeClient()
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("AWS_BEDROCK_MODEL_ID", "test-model-id")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    result = generate_incident_brief(FakeCenter())

    assert result["mode"] == "deterministic_fallback"
    assert "Active incidents: 1" in result["brief"]
    assert "not dispatch authorization" in result["brief"]
    assert "unavailable" in result["aws_note"].lower()


def test_no_model_configured_avoids_importing_aws_sdk(monkeypatch):
    monkeypatch.delenv("AWS_BEDROCK_MODEL_ID", raising=False)

    result = generate_incident_brief(FakeCenter())

    assert result["mode"] == "deterministic_fallback"
    assert "Active incidents: 1" in result["brief"]
    assert "AWS_BEDROCK_MODEL_ID" in result["aws_note"]
