from components.theme import page_setup

page_setup("ResQ Assistant")

from pathlib import Path

import streamlit as st

icon_path = Path(__file__).resolve().parents[1] / "assets" / "resq-chatbot-icon.png"
icon_data = icon_path.read_bytes()
icon_src = "data:image/png;base64," + __import__("base64").b64encode(icon_data).decode("ascii")

st.markdown(
    """
    <style>
    .resq-robot-launcher {
      position: fixed;
      left: 1rem;
      bottom: 1.25rem;
      width: 3.35rem;
      height: 3.35rem;
      border-radius: 999px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #2457c5, #0f766e);
      color: white !important;
      text-decoration: none !important;
      box-shadow: 0 10px 24px rgba(15, 23, 42, .22);
      z-index: 1000002;
      border: 1px solid rgba(255, 255, 255, .25);
      overflow: hidden;
      padding: 0;
    }
    .resq-robot-launcher img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .resq-robot-launcher:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 28px rgba(15, 23, 42, .28);
    }
    </style>
    <a class="resq-robot-launcher" href="#resq-chatbot" title="Open ResQ Assistant" aria-label="Open ResQ Assistant"><img src="{icon_src}" alt="ResQ chatbot"></a>
    <div id="resq-chatbot"></div>
    """,
    unsafe_allow_html=True,
)

from components.chatbot import render_chatbot, smart_emergency_guidance
from components.session import get_center

from resq_mcp.logic import generate_incident_brief

center = get_center()
st.markdown("## AWS Bedrock Response Brief")
st.caption(
    "Generate a coordinator briefing from the current incident and resource snapshot. "
    "Bedrock writes the summary; ResQ-AI's deterministic priority scores remain unchanged."
)

def _secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value or default).strip()

if st.button("Generate Response Brief", type="primary", key="bedrock_response_brief"):
    with st.spinner("Preparing the response brief..."):
        result = generate_incident_brief(
            center,
            model_id=_secret("AWS_BEDROCK_MODEL_ID"),
            region=_secret("AWS_REGION", "us-east-1"),
            aws_access_key_id=_secret("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=_secret("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=_secret("AWS_SESSION_TOKEN"),
        )
    st.session_state["resq_bedrock_brief"] = result

brief_result = st.session_state.get("resq_bedrock_brief")
if brief_result:
    if brief_result["mode"] == "amazon_bedrock":
        st.success(f"Generated with Amazon Bedrock · {brief_result['region']} · {brief_result['model_id']}")
        st.info(brief_result["note"])
    else:
        st.warning("Amazon Bedrock is not connected. This is a basic rules-based summary, not an AI-generated briefing.")
        st.caption(
            "To connect it: open the app's Streamlit Community Cloud settings → Secrets, then add "
            "AWS_BEDROCK_MODEL_ID and AWS_REGION. Add AWS credentials there as private secrets "
            "(or configure an IAM role) with permission to invoke that Bedrock model. Never paste credentials into chat or GitHub."
        )
        st.caption(brief_result.get("aws_note", ""))
    st.text(brief_result["brief"])
    st.caption("Verify all reports, capacities, and recommendations with the responsible coordinator.")

st.markdown("## Smart Emergency Guidance")
st.caption("Choose what is happening and where you are to get immediate, situation-based next steps.")
with st.form("smart_emergency_guidance_form"):
    hazard_col, situation_col = st.columns(2)
    with hazard_col:
        hazard = st.selectbox(
            "What is happening?",
            ["Flood", "Earthquake", "Fire or smoke", "Cyclone or severe storm", "Building collapse", "Other emergency"],
        )
    with situation_col:
        situation = st.selectbox(
            "Where are you right now?",
            ["Indoors", "Outdoors", "In a vehicle", "Near water", "Not sure"],
        )
    injured_col, trapped_col = st.columns(2)
    with injured_col:
        injured = st.checkbox("Someone is injured")
    with trapped_col:
        trapped = st.checkbox("Someone is trapped")
    guidance_submitted = st.form_submit_button("Show next steps", type="primary")

if guidance_submitted:
    st.session_state["smart_emergency_guidance"] = smart_emergency_guidance(
        hazard, situation, injured=injured, trapped=trapped
    )
if st.session_state.get("smart_emergency_guidance"):
    st.warning("If there is immediate danger, call emergency services now. Do not delay to use this app.", icon="🚨")
    st.markdown(st.session_state["smart_emergency_guidance"])

render_chatbot(center)
