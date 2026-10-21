from components.theme import page_setup

page_setup("ResQ Assistant")

import streamlit as st

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
      font-size: 1.55rem;
      line-height: 1;
    }
    .resq-robot-launcher:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 28px rgba(15, 23, 42, .28);
    }
    </style>
    <a class="resq-robot-launcher" href="#resq-chatbot" title="Open ResQ Assistant" aria-label="Open ResQ Assistant">🤖</a>
    <div id="resq-chatbot"></div>
    """,
    unsafe_allow_html=True,
)

from components.chatbot import render_chatbot
from components.session import get_center

render_chatbot(get_center())
