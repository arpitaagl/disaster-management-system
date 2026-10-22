# Alexa+ hackathon integration

ResQ-AI adds a read-only MCP server and a polished web-based response-assistant page. The self-hosted MCP server is the primary Alexa+ track artifact; the Streamlit assistant provides the conversational demo surface. The hackathon's official rules require a self-hosted MCP server using MCP spec 2025-11-25 or later over Streamable HTTP, or an Agent Skill; the rules also allow a web-based simulated experience. See the [official rules](https://amazonappdev2026.devpost.com/rules) and [Alexa+ MCP requirements](https://www.developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-quickstart).

## Implemented MCP tools

- `list_incidents`: list active/resolved/all incidents ordered by existing deterministic priority score.
- `get_incident_details`: inspect an incident's current recommendation and priority breakdown.
- `explain_priority`: return the existing deterministic score and component breakdown.
- `get_resource_status`: report rescue-team availability, hospital beds, and shelter spaces.
- `find_shelters`: find demo shelters with a minimum number of free spaces.
- `generate_incident_brief`: create a deterministic briefing, or use Amazon Bedrock Converse when configured.

The tools are read-only. They never modify priority scores, allocate resources, or authorize dispatch. The MCP server loads the prepared simulated flood scenario when it starts; this is a demo snapshot, not a live feed or shared Streamlit session state.

## Run the Streamlit app

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open **ResQ Assistant** in the Streamlit multipage navigation. Without an LLM key, built-in deterministic question patterns still work. To enable the existing OpenAI-compatible chat provider, set `OPENAI_API_KEY`, and optionally `OPENAI_BASE_URL` and `OPENAI_MODEL`, in `.env` or Streamlit secrets. Never commit real credentials.

## Run the MCP server

```bash
python -m resq_mcp.server
```

By default, the Streamable HTTP endpoint is `http://127.0.0.1:8000/mcp`. Configure `MCP_HOST` and `MCP_PORT` if needed. Connect an MCP client/Inspector to this endpoint for local testing. You can also use the included real MCP client demo in a second terminal:\n\n```bash\npython -m resq_mcp.demo_client\npython -m resq_mcp.demo_client --tool explain_priority --incident-id INC-001\npython -m resq_mcp.demo_client --tool find_shelters --minimum-spaces 10\n```\n\nThe demo client performs MCP initialization, lists the server's registered tools, and calls a selected tool over Streamable HTTP. A remote Alexa+ integration requires a publicly reachable HTTPS endpoint and Alexa+'s authentication/account-linking requirements; the local development server is intentionally not exposed publicly and does not implement OAuth. The Alexa+ partner-only CLI/toolkit is not required to submit a self-hosted MCP server, but direct Alexa+ account linking is not claimed by this prototype. Do not expose an unauthenticated local endpoint to the internet.

## AWS Builder mini-challenge: optional Amazon Bedrock integration

The `generate_incident_brief` tool integrates with Amazon Bedrock's Converse API when `AWS_BEDROCK_MODEL_ID` is set. It uses the standard AWS credential chain (environment, shared profile, or IAM role), and `AWS_REGION` defaults to `us-east-1`.

Set these local environment variables (do not put AWS credentials in source control):

```bash
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=your-enabled-bedrock-model-id
```

Install dependencies, configure AWS credentials outside the repository, enable access to the selected model, and run the MCP server. Call `generate_incident_brief` to exercise Bedrock. If no model ID is configured or the service is unavailable, the tool returns a deterministic briefing instead. For an eligible AWS Builder submission, demonstrate a successful Bedrock call and document the actual AWS services and permissions used in your submission's product feedback.

Scope IAM permissions to the selected model and region; avoid long-lived credentials in deployed environments. Bedrock output is narrative only. Deterministic incident scoring remains in `core/priority.py` and `core/state.py`.

## Suggested demo sequence (3–4 minutes)

1. Launch Streamlit and load the demo disaster scenario.
2. Show the incident queue, deterministic score, map, and resource recommendation.
3. Open **ResQ Assistant** and ask “Which incident is most urgent?”, “Explain INC-001”, and “Which shelters have space?”.
4. Start `python -m resq_mcp.server` in a terminal and connect with an MCP Inspector/client.
5. Call `list_incidents`, `explain_priority`, and `find_shelters` to show MCP tool responses over Streamable HTTP.
6. If Bedrock credentials/model access are configured, call `generate_incident_brief` and confirm the response mode is `amazon_bedrock`; otherwise show the deterministic fallback honestly.

## Safety and demo limitations

- Bundled scenario records are simulated with Pune-area coordinates; no government or responder feed is connected.
- Distance calculations are prototype estimates, not verified route times.
- MCP tools are intentionally read-only. Human coordinators remain responsible for verification and operational decisions.
- A public Alexa+ deployment needs HTTPS, authentication/account linking and the official discovery/authorization endpoints; this branch provides local Streamable HTTP for development and MCP-client demoing, not production Alexa+ onboarding.
