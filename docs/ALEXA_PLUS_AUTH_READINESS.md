# Alexa+ authentication readiness audit

## Current status

**Status: not production-ready for direct Alexa+ onboarding.**

The ResQ-AI MCP server currently uses the MCP Python SDK over Streamable HTTP and registers read-only disaster-response tools. The repository does not currently implement the OAuth authorization/resource-server endpoints required for an authenticated public Alexa+ integration. A local MCP endpoint is not a production deployment.

This document records the implementation boundary; it does not claim that authentication has been implemented or tested.

## Current implementation

- [x] MCP server uses Streamable HTTP transport.
- [x] Tools are read-only and preserve deterministic incident priority scoring.
- [x] Tool descriptions warn that demo state is simulated and operational decisions require human verification.
- [x] Local MCP client tests exercise tool argument mapping.
- [ ] Public HTTPS deployment and operational monitoring.
- [x] Auth0 JWT verification and required-scope enforcement implemented on `phase3/alexa-service-auth` (pending local tests and review; not deployed).
- [ ] Protected-resource metadata discovery (RFC 9728) and authorization-server metadata.
- [ ] OAuth 2.1 authorization-code flow with PKCE S256 and the required resource/audience validation, if required for the selected Alexa+ integration.
- [x] Token signature, issuer, audience, expiry, subject, and `read:incidents` scope validation implemented with negative tests (pending local test run).
- [ ] User account linking and refresh-token handling, if user-specific identity or data is introduced.
- [ ] End-to-end verification with the official Alexa+ onboarding/toolkit flow.

## Required implementation decisions

1. Select and configure a supported OAuth provider (for example, Amazon Cognito or another provider supported by the target deployment).
2. Confirm the current official Alexa+ MCP authentication contract for the intended integration, including whether service-level client-credentials authentication, user-level account linking, or both are required.
3. Deploy behind HTTPS and configure the exact public MCP resource URL, issuer, audience/resource, scopes, and redirect/registration details with the chosen provider.
4. Implement or configure the provider-backed protected-resource and authorization-server metadata endpoints as required by that contract.
5. Ensure every protected MCP request validates a bearer token server-side. Never accept a token supplied in a query parameter; never log access tokens or secrets.
6. Add tests for unauthenticated requests, malformed/expired/wrong-audience tokens, insufficient scopes, metadata contents, and successful authorized tool calls.
7. Re-run the complete test suite and manually verify the deployed flow before claiming Alexa+ production readiness.

## Safety and scope

- Do not add placeholder authentication that merely checks whether an environment variable exists.
- Do not expose the unauthenticated development endpoint to the public internet.
- Do not put client secrets, access tokens, AWS credentials, or provider credentials in source control.
- Do not change deterministic priority scoring, dispatch behavior, or resource assignment as part of authentication work.
- Keep all MCP tools read-only unless a separately reviewed safety design explicitly authorizes otherwise.

## References

- [Alexa+ MCP Toolkit Quickstart](https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-quickstart)
- [Alexa+ MCP Authentication](https://developer.amazon.com/docs/alexaplus/add-ons/category-sdk-mcp-authentication)
- [Alexa+ MCP Toolkit Account Linking](https://developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-account-linking)
- [RFC 9728: OAuth 2.0 Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728)
- [RFC 8414: OAuth 2.0 Authorization Server Metadata](https://www.rfc-editor.org/rfc/rfc8414)

## Auth0 resource-server configuration (branch implementation)

The current branch adds an Auth0 JWT verifier to the MCP server. Authentication is enabled only when all three environment variables are set; a partial configuration prevents startup. If all three are absent, the server remains in local-development mode and **must not be exposed publicly**.

Set these values in the deployment environment (never commit credentials):

- `AUTH0_DOMAIN=arpitaagl.us.auth0.com` (hostname only, no scheme or path)
- `AUTH0_AUDIENCE=https://resq-ai-mcp` (the Auth0 API Identifier)
- `MCP_PUBLIC_URL=https://YOUR-DEPLOYED-HOST/YOUR-MCP-PATH` (replace with the exact public HTTPS MCP resource URL)

The Auth0 API must define the `read:incidents` scope and the machine-to-machine application must be authorized to request it. Request a token using the Auth0 client-credentials flow with both `audience=https://resq-ai-mcp` and `scope=read:incidents`. Keep the client secret in deployment secrets/environment variables; it is not needed by the MCP resource server and must not be added to this repository.

The verifier accepts only RS256-signed JWTs from the configured Auth0 issuer and validates signature, issuer, API audience, expiry, required claims, and scope. It fails closed if token verification or JWKS retrieval fails. The MCP SDK is also configured to bind verified tokens to the configured public resource URL.

This is not yet a claim of production readiness: run the full test suite, confirm the deployed URL and metadata, verify the exact Alexa+ authentication contract, and complete end-to-end onboarding before public exposure.
