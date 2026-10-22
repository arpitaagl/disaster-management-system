# AWS Builder mini-challenge: Amazon Bedrock incident brief

## What this integration does

ResQ-AI exposes a read-only MCP tool named `generate_incident_brief`. It creates a concise operational summary from the current ResQ-AI server snapshot. When `AWS_BEDROCK_MODEL_ID` is configured, it calls Amazon Bedrock Runtime's Converse API through Boto3. If the model is not configured or the request fails, it returns a deterministic fallback instead.

The model generates narrative only. Incident priority scores remain calculated by ResQ-AI's deterministic engine, and the brief must not authorize dispatch. The MCP server currently loads a **simulated demo scenario**, not a live emergency feed or the active Streamlit session.

## Configure a real Bedrock call

1. Use an AWS account with Amazon Bedrock model access enabled for the selected model and region.
2. Configure AWS credentials using the standard AWS credential chain or an appropriate IAM role. Never commit credentials or paste them into GitHub.
3. In the environment where the MCP server runs, set:

   ```bash
   AWS_REGION=us-east-1
   AWS_BEDROCK_MODEL_ID=your-enabled-bedrock-model-id
   ```

   Choose a model ID that is actually enabled in your account and region. The model ID above is a placeholder.
4. Install dependencies and start the server:

   ```bash
   pip install -r requirements.txt
   python -m resq_mcp.server
   ```

5. In a second terminal, call the briefing tool through the included MCP client:

   ```bash
   python -m resq_mcp.demo_client --tool generate_incident_brief
   ```

6. Confirm the tool response has `"mode": "amazon_bedrock"` and includes the generated brief. If it says `"mode": "deterministic_fallback"`, the real Bedrock integration has **not** been demonstrated yet. Check model access, region, credentials, and the model ID; do not present a fallback as a successful Bedrock call.

## Evidence to capture for the submission

- A terminal or MCP Inspector screenshot showing the `generate_incident_brief` call and `mode: amazon_bedrock`.
- The AWS Region and model identifier used (do not show credentials, access keys, or tokens).
- A short explanation: “Amazon Bedrock Converse turns ResQ-AI's incident snapshot into a readable coordinator briefing. Deterministic scoring stays outside the model; the tool is read-only and requires human verification.”
- The repository URL and this document URL.

## Tests and limitations

Run the local contract tests with:

```bash
pytest -q tests/test_bedrock_briefing.py tests/test_resq_mcp.py
```

These tests mock Boto3 and verify successful-response handling, region/model configuration, and fallback behavior. They do **not** prove AWS credentials, model access, or a live Bedrock request. A real call and screenshot are still required for evidence of runtime use.

The integration is for hackathon demonstration only. The bundled incident/resource scenario is simulated, reported capacities may not be current, and the tool does not dispatch responders or replace emergency authorities.

## Official API reference

Amazon Bedrock Converse API: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
