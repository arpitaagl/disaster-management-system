"""Auth0 JWT validation for the read-only ResQ-AI MCP resource server."""
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier

REQUIRED_SCOPE = "read:incidents"


class Auth0JWTVerifier(TokenVerifier):
    """Validate Auth0 RS256 access tokens against issuer, audience, expiry, and scope."""

    def __init__(self, domain: str, audience: str, resource_url: str) -> None:
        domain = domain.strip().rstrip("/")
        if not domain or "/" in domain or "://" in domain:
            raise ValueError("AUTH0_DOMAIN must be a hostname, not a URL or path")
        if not audience.strip():
            raise ValueError("AUTH0_AUDIENCE must not be empty")
        self.issuer = f"https://{domain}/"
        self.audience = audience.strip()
        self.resource_url = resource_url.strip()
        self.jwks = PyJWKClient(f"https://{domain}/.well-known/jwks.json")

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return an MCP AccessToken only when every security check succeeds."""
        try:
            signing_key = self.jwks.get_signing_key_from_jwt(token).key
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
                leeway=0,
            )
            raw_scope = claims.get("scope", "")
            scopes = raw_scope.split() if isinstance(raw_scope, str) else []
            if REQUIRED_SCOPE not in scopes:
                return None
            subject = claims.get("sub")
            if not isinstance(subject, str) or not subject:
                return None
            exp = claims.get("exp")
            if not isinstance(exp, (int, float)) or exp <= time.time():
                return None
            return AccessToken(
                token=token,
                client_id=str(claims.get("azp") or claims.get("client_id") or subject),
                scopes=scopes,
                expires_at=int(exp),
                resource=self.resource_url,
                subject=subject,
                claims=claims,
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            return None
        except Exception:
            # JWKS/network/key lookup failures must fail closed, never allow access.
            return None


def auth_configuration() -> tuple[Auth0JWTVerifier, Any] | None:
    """Build MCP auth settings; fail closed on partial or missing public configuration."""
    domain = os.getenv("AUTH0_DOMAIN", "").strip()
    audience = os.getenv("AUTH0_AUDIENCE", "").strip()
    public_url = os.getenv("MCP_PUBLIC_URL", "").strip()
    configured = (bool(domain), bool(audience), bool(public_url))
    if not any(configured):
        # Local development may run without Auth0, but a public Render deployment may not.
        if os.getenv("RENDER", "").strip().lower() == "true":
            raise RuntimeError(
                "Public Render deployments require AUTH0_DOMAIN, AUTH0_AUDIENCE, and "
                "MCP_PUBLIC_URL. Configure all three before starting the MCP service."
            )
        return None
    if not all(configured):
        raise RuntimeError(
            "Configure AUTH0_DOMAIN, AUTH0_AUDIENCE, and MCP_PUBLIC_URL together; "
            "refusing to start with a partial authentication configuration."
        )
    parsed = urlparse(public_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise RuntimeError("MCP_PUBLIC_URL must be the exact public HTTPS MCP endpoint URL.")
    from pydantic import AnyHttpUrl
    from mcp.server.auth.settings import AuthSettings

    verifier = Auth0JWTVerifier(domain=domain, audience=audience, resource_url=public_url)
    settings = AuthSettings(
        issuer_url=AnyHttpUrl(verifier.issuer),
        resource_server_url=AnyHttpUrl(public_url),
        required_scopes=[REQUIRED_SCOPE],
        validate_token_resource=True,
    )
    return verifier, settings
