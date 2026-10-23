from components.theme import page_setup

page_setup("ResQ Assistant")

import streamlit as st

# Restore the original assistant-page avatar shortcut.
from pathlib import Path
import base64

icon_path = Path(__file__).resolve().parents[1] / "assets" / "resq-chatbot-icon.png"
icon_data = icon_path.read_bytes()
icon_src = "data:image/png;base64," + base64.b64encode(icon_data).decode("ascii")

st.markdown(
    f"""
    <style>
    .resq-robot-launcher {{
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
    }}
    .resq-robot-launcher img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .resq-robot-launcher:hover {{
      transform: translateY(-2px);
      box-shadow: 0 14px 28px rgba(15, 23, 42, .28);
    }}
    </style>
    <a class="resq-robot-launcher" href="#resq-chatbot" title="Open ResQ Assistant" aria-label="Open ResQ Assistant"><img src="{icon_src}" alt="ResQ chatbot"></a>
    <div id="resq-chatbot"></div>
    """,
    unsafe_allow_html=True,
)

from components.chatbot import render_chatbot, smart_emergency_guidance
from components.session import get_center

center = get_center()

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
