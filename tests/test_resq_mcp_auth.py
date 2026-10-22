"""Security regression tests for Auth0-backed MCP token verification."""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from resq_mcp.auth import Auth0JWTVerifier, REQUIRED_SCOPE, auth_configuration


@pytest.fixture
def verifier_and_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = Auth0JWTVerifier(
        domain="example.auth0.com",
        audience="https://resq-ai-mcp",
        resource_url="https://resq.example.com/mcp",
    )
    verifier.jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private_key.public_key())
    )
    return verifier, private_key


def make_token(private_key, **overrides):
    now = int(time.time())
    claims = {
        "iss": "https://example.auth0.com/",
        "aud": "https://resq-ai-mcp",
        "sub": "client|resq-service",
        "iat": now - 1,
        "exp": now + 300,
        "scope": REQUIRED_SCOPE,
        "azp": "resq-service-client",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


def test_valid_token_is_accepted_and_bound_to_expected_resource(verifier_and_keys):
    verifier, private_key = verifier_and_keys
    token = make_token(private_key)

    result = asyncio.run(verifier.verify_token(token))

    assert result is not None
    assert result.scopes == [REQUIRED_SCOPE]
    assert result.client_id == "resq-service-client"
    assert result.subject == "client|resq-service"
    assert result.resource == "https://resq.example.com/mcp"


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://attacker.example/"},
        {"aud": "https://another-api"},
        {"exp": int(time.time()) - 60},
        {"scope": "other:scope"},
        {"scope": ""},
        {"sub": ""},
    ],
)
def test_invalid_claims_are_rejected(verifier_and_keys, overrides):
    verifier, private_key = verifier_and_keys
    token = make_token(private_key, **overrides)

    assert asyncio.run(verifier.verify_token(token)) is None


def test_malformed_token_is_rejected(verifier_and_keys):
    verifier, _ = verifier_and_keys

    assert asyncio.run(verifier.verify_token("not.a.jwt")) is None


def test_auth_is_disabled_only_when_all_auth_settings_are_absent(monkeypatch):
    monkeypatch.delenv("AUTH0_DOMAIN", raising=False)
    monkeypatch.delenv("AUTH0_AUDIENCE", raising=False)
    monkeypatch.delenv("MCP_PUBLIC_URL", raising=False)
    monkeypatch.delenv("RENDER", raising=False)

    assert auth_configuration() is None


def test_public_render_deployment_requires_auth_configuration(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("AUTH0_DOMAIN", raising=False)
    monkeypatch.delenv("AUTH0_AUDIENCE", raising=False)
    monkeypatch.delenv("MCP_PUBLIC_URL", raising=False)

    with pytest.raises(RuntimeError, match="Public Render deployments require"):
        auth_configuration()


def test_partial_auth_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("AUTH0_DOMAIN", "example.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://resq-ai-mcp")
    monkeypatch.delenv("MCP_PUBLIC_URL", raising=False)

    with pytest.raises(RuntimeError, match="together"):
        auth_configuration()


def test_public_resource_url_must_use_https(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("AUTH0_DOMAIN", "example.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://resq-ai-mcp")
    monkeypatch.setenv("MCP_PUBLIC_URL", "http://localhost:8000/mcp")

    with pytest.raises(RuntimeError, match="HTTPS"):
        auth_configuration()
