"""Command-center visual theme."""

from __future__ import annotations

import streamlit as st

from core.config import DISCLAIMER
from core.llm_client import llm_configured
from core.state import CommandCenter


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

.resq-chat-overlay { display: none; }

:root {
  color-scheme: light;
  --resq-ink: #152238;
  --resq-muted: #66758b;
  --resq-border: #e2e8f0;
  --resq-panel: #ffffff;
  --resq-canvas: #f5f7fb;
  --resq-blue: #2457c5;
  --resq-teal: #0f766e;
  --resq-red: #c2414b;
  --resq-radius: 14px;
  --resq-shadow: 0 8px 24px rgba(22,34,56,.045);
}

html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: "DM Sans", sans-serif;
  color: var(--resq-ink);
}
.stApp {
  background: var(--resq-canvas);
  color: var(--resq-ink);
}
[data-testid="stHeader"] {
  background: rgba(245,247,251,.92);
}
/* Keep Streamlit's header and toolbar mounted so its native sidebar
   reopen control continues to exist after the sidebar is collapsed.
   Hide only the cloud toolbar actions (Fork/GitHub/Deploy). */
[data-testid="stToolbar"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
  background: transparent !important;
}
[data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"],
[data-testid="stToolbar"] a[href*="github.com"],
[data-testid="stToolbar"] a[aria-label*="GitHub"],
[data-testid="stToolbar"] button[aria-label*="Deploy"],
[data-testid="stToolbar"] button[aria-label*="GitHub"],
[data-testid="stDecoration"],
#MainMenu,
footer {
  display: none !important;
  visibility: hidden !important;
}

/* Keep the real native sidebar toggle accessible in both states. */
header[data-testid="stHeader"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  height: 3.5rem !important;
  min-height: 3.5rem !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: visible !important;
  background: transparent !important;
  position: relative !important;
  z-index: 999998 !important;
}
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebar"] button[aria-label*="Collapse"],
button[aria-label*="Collapse sidebar"],
button[aria-label*="Expand sidebar"] {
  display: inline-flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
  align-items: center !important;
  justify-content: center !important;
  width: 44px !important;
  min-width: 44px !important;
  height: 44px !important;
  min-height: 44px !important;
  border: 1px solid #9ca3af !important;
  border-radius: 10px !important;
  background: #e5e7eb !important;
  color: #374151 !important;
  box-shadow: 0 3px 10px rgba(31,41,55,.18) !important;
  z-index: 1000001 !important;
}
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapsedControl"],
button[data-testid="stSidebarCollapsedControl"] {
  position: fixed !important;
  top: 12px !important;
  left: 12px !important;
}
[data-testid="collapsedControl"] svg,
[data-testid="collapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapsedControl"] svg,
button[aria-label*="Collapse sidebar"] svg,
button[aria-label*="Expand sidebar"] svg,
[data-testid="stSidebar"] button[aria-label*="Collapse"] svg {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  color: #374151 !important;
  fill: currentColor !important;
  stroke: currentColor !important;
}
[data-testid="collapsedControl"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
button[aria-label*="Collapse sidebar"]:hover,
button[aria-label*="Expand sidebar"]:hover {
  background: #d1d5db !important;
  border-color: #6b7280 !important;
  box-shadow: 0 4px 12px rgba(31,41,55,.24) !important;
}
[data-testid="stAppViewContainer"] {
  padding-top: 0 !important;
}
[data-testid="stMainBlockContainer"] {
  padding-top: .55rem;
  padding-bottom: 3rem;
  max-width: 1600px;
}
section[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid var(--resq-border);
}
section[data-testid="stSidebar"] > div {
  padding-top: 1.25rem;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: var(--resq-muted);
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
  color: var(--resq-ink);
  letter-spacing: -.03em;
}
h1, h2, h3, h4, h5 {
  color: var(--resq-ink);
  letter-spacing: -.035em;
}
h1 { font-weight: 750 !important; line-height: 1.12 !important; }
h2 { font-size: clamp(1.35rem, 1.7vw, 1.65rem) !important; }
h2, h3 { font-weight: 700 !important; }
h3 { font-size: 1.12rem !important; }
h4, h5 { font-weight: 650 !important; }
[data-testid="stMarkdownContainer"] p { line-height: 1.65; }
.stMarkdown, [data-testid="stVerticalBlock"] > [data-testid="element-container"] { scroll-margin-top: 1rem; }
::selection { background: #c9d8ff; color: #152238; }
p, label, li, [data-testid="stMarkdownContainer"] {
  color: var(--resq-ink);
}
small, .stCaption, [data-testid="stCaptionContainer"] {
  color: var(--resq-muted) !important;
}
a { color: var(--resq-blue) !important; }

button[kind="secondary"]:hover {
  border-color: var(--resq-blue) !important;
}

/* Main command-center header */
.resq-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 10px 0 22px;
  border-bottom: 1px solid var(--resq-border);
  margin-bottom: 26px;
  padding-top: 14px;
  padding-bottom: 24px;
}
.resq-kicker {
  color: var(--resq-blue);
  letter-spacing: .16em;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.resq-title {
  font-size: clamp(26px, 2.3vw, 35px);
  line-height: 1.15;
  font-weight: 750;
  color: var(--resq-ink);
  margin: 0;
  letter-spacing: -.045em;
}
.resq-sub {
  color: var(--resq-muted);
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.55;
  max-width: 780px;
}
.resq-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.pill {
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  font-weight: 600;
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid #dbe4f0;
  background: #f8fafc;
  color: #34445b;
  white-space: nowrap;
}
.pill.ok { border-color: #b7e4d4; color: #116149; background: #eaf8f1; }
.pill.warn { border-color: #f1d5a4; color: #8a4b0b; background: #fff7e8; }
.pill.bad { border-color: #f0c4c7; color: #a72c37; background: #fff0f1; }

.metric-card {
  background: var(--resq-panel);
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 17px 18px 15px;
  min-height: 104px;
  box-shadow: var(--resq-shadow);
  transition: box-shadow .18s ease, border-color .18s ease;
}
.metric-card .label {
  color: var(--resq-muted);
  font-size: 11px;
  letter-spacing: .08em;
  font-weight: 700;
  text-transform: uppercase;
}
.metric-card .value {
  font-size: 30px;
  line-height: 1.15;
  font-weight: 700;
  color: var(--resq-ink);
  margin-top: 10px;
  font-family: "IBM Plex Mono", monospace;
}
.metric-card.critical .value { color: var(--resq-red); }
.metric-card.medical .value { color: #b66a12; }
.panel {
  background: #fff;
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 18px;
  box-shadow: var(--resq-shadow);
  transition: box-shadow .18s ease, border-color .18s ease;
}
.event-line {
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  color: #475569;
  padding: 7px 0;
  border-bottom: 1px solid #edf1f6;
}
.disclaimer {
  color: var(--resq-muted);
  font-size: 12px;
  margin-top: 10px;
}

div[data-testid="stMetric"] {
  background: #fff;
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: var(--resq-shadow);
  transition: border-color .18s ease, box-shadow .18s ease;
}
div[data-testid="stMetricLabel"] p {
  color: var(--resq-muted) !important;
  font-size: 12px;
  font-weight: 600;
}
div[data-testid="stMetricValue"] {
  color: var(--resq-ink);
  font-family: "IBM Plex Mono", monospace;
}
.stDataFrame, [data-testid="stDataFrame"] {
  border: 1px solid var(--resq-border);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(22,34,56,.025);
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--resq-border);
  border-radius: 14px;
}
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 9px;
  font-weight: 600;
  border: 1px solid #d5deeb;
  transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  border-color: #9db7ee;
  box-shadow: 0 3px 10px rgba(36,87,197,.10);
  transform: translateY(-1px);
}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: var(--resq-blue);
  border-color: var(--resq-blue);
  color: #fff;
}
input, textarea, [data-baseweb="select"] > div {
  border-radius: 10px !important;
}
input:focus, textarea:focus, [data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within {
  border-color: #7da0eb !important;
  box-shadow: 0 0 0 3px rgba(36,87,197,.12) !important;
}
[data-testid="stSelectbox"], [data-testid="stTextInput"], [data-testid="stTextArea"], [data-testid="stNumberInput"], [data-testid="stDateInput"] { margin-bottom: .35rem; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid var(--resq-border); }
[data-testid="stTabs"] [data-baseweb="tab"] { padding: 10px 14px; border-radius: 9px 9px 0 0; font-weight: 600; }
[data-testid="stTabs"] [aria-selected="true"] { color: var(--resq-blue) !important; }
[data-testid="stExpander"] { border: 1px solid var(--resq-border); border-radius: 12px; background: var(--resq-panel); }
[data-testid="stExpander"] summary { font-weight: 600; }
[data-testid="stProgressBar"] > div > div { border-radius: 99px; }
[data-testid="stAlert"] p { line-height: 1.55; }
[data-testid="stFileUploader"], [data-testid="stCameraInput"] { border-radius: 12px; }
[data-testid="stSidebarNav"] { padding-top: .35rem; }
[data-testid="stSidebarNav"] a { border-radius: 9px; margin: 2px 6px; transition: background .15s ease; }
/* Label the main app.py entrypoint as the Live Disaster Intelligence landing page. */
[data-testid="stSidebarNav"] > ul > li:first-child a {
  font-size: 0 !important;
}
[data-testid="stSidebarNav"] > ul > li:first-child a::after {
  content: "Live Disaster Intelligence";
  font-size: .91rem;
  letter-spacing: -.01em;
}
/* Hide Streamlit's default app icon and page-options ellipsis for the landing item. */
[data-testid="stSidebarNav"] > ul > li:first-child a > span,
[data-testid="stSidebarNav"] > ul > li:first-child a > svg,
[data-testid="stSidebarNav"] > ul > li:first-child a [data-testid="stIconMaterial"],
[data-testid="stSidebarNav"] > ul > li:first-child button {
  display: none !important;
}
[data-testid="stSidebarNav"] a:hover { background: #eef3fb; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: #eaf0ff; color: #204db0 !important; font-weight: 700; }
button[kind="primary"] { font-weight: 700 !important; }
.stDownloadButton > button { width: 100%; border-radius: 10px; font-weight: 650; }
.stLinkButton > a { border-radius: 9px; font-weight: 600; }
.metric-card:hover, .panel:hover, div[data-testid="stMetric"]:hover { border-color: #ccd8eb; box-shadow: 0 8px 24px rgba(22,34,56,.055); }
[data-testid="stChatMessage"] {
  background: #fff;
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 10px;
}
[data-testid="stChatInput"] {
  border-color: #d6dfeb;
  border-radius: 14px;
  background: #fff;
}
[data-testid="stAlert"] {
  border-radius: 12px;
}
hr {
  border-color: var(--resq-border);
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
@media (max-width: 850px) {
  .resq-header { flex-direction: column; }
  .resq-pills { justify-content: flex-start; }
  .resq-title { font-size: 24px; }
}
</style>
"""


DARK_CSS = """
<style>
:root { color-scheme: dark; --resq-ink:#e6edf7; --resq-muted:#a3b1c6; --resq-border:#303d50; --resq-panel:#172234; --resq-canvas:#0d1420; --resq-blue:#8ab4ff; --resq-red:#ff858d; }
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] { background:var(--resq-canvas)!important; color:var(--resq-ink)!important; }
html,body,[class*="css"],p,label,li,[data-testid="stMarkdownContainer"] { color:var(--resq-ink); }
[data-testid="stHeader"] { background:rgba(13,20,32,.94)!important; }
section[data-testid="stSidebar"] { background:#111b2a!important; border-right-color:var(--resq-border)!important; }
[data-testid="stSidebarNav"] { color:var(--resq-ink)!important; }
[data-testid="stSidebarNav"] a { color:#d7e2f0!important; }
[data-testid="stSidebarNav"] a:hover { background:#202d40!important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background:#243653!important; color:#c5d9ff!important; font-weight:700; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom-color:var(--resq-border); }
[data-testid="stTabs"] [aria-selected="true"] { color:#9fc2ff!important; }
[data-testid="stExpander"] { background:var(--resq-panel)!important; border-color:var(--resq-border)!important; }
.metric-card:hover, .panel:hover, div[data-testid="stMetric"]:hover { border-color:#435775!important; box-shadow:none!important; }
input:focus,textarea:focus,[data-baseweb="input"]:focus-within,[data-baseweb="select"]:focus-within { border-color:#8ab4ff!important; box-shadow:0 0 0 3px rgba(138,180,255,.14)!important; }
h1,h2,h3,h4,h5,.resq-title,.metric-card .value,div[data-testid="stMetricValue"] { color:var(--resq-ink)!important; }
small,.stCaption,[data-testid="stCaptionContainer"],.resq-sub,.disclaimer { color:var(--resq-muted)!important; }
a { color:#9fc2ff!important; }
.metric-card,.panel,div[data-testid="stMetric"],[data-testid="stChatMessage"],[data-testid="stChatInput"],[data-testid="stVerticalBlockBorderWrapper"] { background:var(--resq-panel)!important; border-color:var(--resq-border)!important; color:var(--resq-ink)!important; box-shadow:none!important; }
.event-line { color:#c4d0e0; border-bottom-color:var(--resq-border); }
.pill { background:#202d40; color:#dbe7f7; border-color:#394b63; }
.pill.ok { background:#123a34; color:#9de7cb; border-color:#286b5b; }
.pill.warn { background:#3b2c18; color:#ffd28a; border-color:#755327; }
.pill.bad { background:#3e2029; color:#ffadb4; border-color:#7d3947; }
div[data-testid="stMetricLabel"] p { color:var(--resq-muted)!important; }
.stDataFrame,[data-testid="stDataFrame"] { border-color:var(--resq-border)!important; }
.stButton>button,[data-testid="stFormSubmitButton"]>button { background:#202d40; color:var(--resq-ink); border-color:#40516a; }
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"]>button[kind="primary"] { background:#315fb7; border-color:#4778d2; color:#fff; }
input,textarea,[data-baseweb="select"]>div,[data-baseweb="input"]>div,[data-baseweb="textarea"]>div { background:#172234!important; color:var(--resq-ink)!important; border-color:#40516a!important; }
input::placeholder,textarea::placeholder { color:#91a0b5!important; }
[data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"],[data-baseweb="option"] { background:#172234!important; color:var(--resq-ink)!important; }
[data-baseweb="option"]:hover { background:#263750!important; }
[data-testid="stAlert"] { background:#172234; border-color:var(--resq-border); }
[data-testid="stPopover"],[data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"] {
  background:#172234!important; color:var(--resq-ink)!important;
}
[data-testid="stSidebar"] button:focus-visible,
[data-testid="stSidebarNav"] a:focus-visible,
.stButton>button:focus-visible,
[data-testid="stFormSubmitButton"]>button:focus-visible {
  outline:2px solid #5eead4!important; outline-offset:2px!important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color:var(--resq-muted)!important;
}
hr { border-color:var(--resq-border)!important; }

/* Comprehensive dark-mode overrides. These intentionally out-rank the light-theme
   form/card rules declared by POLISH_CSS earlier in this file. */
:root {
  color-scheme: dark !important;
  --resq-ink: #e7eef8 !important;
  --resq-muted: #a8b8cc !important;
  --resq-border: #33465d !important;
  --resq-panel: #152235 !important;
  --resq-canvas: #0b1421 !important;
  --resq-blue: #8abaff !important;
  --resq-teal: #5eead4 !important;
}
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background-color: #0b1421 !important;
  color: #e7eef8 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"],
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMainBlockContainer"] [data-testid="stExpander"],
[data-testid="stMainBlockContainer"] [data-testid="stContainer"],
[data-testid="stMainBlockContainer"] [data-testid="stPopover"],
[data-testid="stMainBlockContainer"] [data-testid="stChatMessage"],
[data-testid="stMainBlockContainer"] [data-testid="stChatInput"],
[data-testid="stMainBlockContainer"] [data-testid="stMetric"],
[data-testid="stMainBlockContainer"] .panel,
[data-testid="stMainBlockContainer"] .metric-card {
  background: #152235 !important;
  color: #e7eef8 !important;
  border-color: #33465d !important;
  box-shadow: none !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] label,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] p,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] li,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] strong,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] em,
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] {
  color: #dce7f5 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] input,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] textarea,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="select"] > div,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="input"],
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="textarea"],
[data-testid="stMainBlockContainer"] input,
[data-testid="stMainBlockContainer"] textarea,
[data-testid="stMainBlockContainer"] [data-baseweb="input"],
[data-testid="stMainBlockContainer"] [data-baseweb="textarea"],
[data-testid="stMainBlockContainer"] [data-baseweb="select"] > div,
[data-testid="stMainBlockContainer"] [data-testid="stDateInput"] input,
[data-testid="stMainBlockContainer"] [data-testid="stTimeInput"] input {
  background: #0e1a2a !important;
  color: #f1f6fd !important;
  -webkit-text-fill-color: #f1f6fd !important;
  border-color: #405670 !important;
  box-shadow: none !important;
}
[data-testid="stMainBlockContainer"] input::placeholder,
[data-testid="stMainBlockContainer"] textarea::placeholder {
  color: #91a6bf !important;
  -webkit-text-fill-color: #91a6bf !important;
  opacity: 1 !important;
}
[data-testid="stMainBlockContainer"] [data-baseweb="select"] span,
[data-testid="stMainBlockContainer"] [data-baseweb="select"] div,
[data-testid="stMainBlockContainer"] [data-baseweb="input"] div,
[data-testid="stMainBlockContainer"] [data-baseweb="textarea"] div {
  color: #e7eef8 !important;
}
[data-testid="stMainBlockContainer"] [data-baseweb="select"] svg,
[data-testid="stMainBlockContainer"] [data-baseweb="input"] svg {
  fill: #c3d3e7 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stRadio"] label,
[data-testid="stMainBlockContainer"] [data-testid="stCheckbox"] label,
[data-testid="stMainBlockContainer"] [data-testid="stToggle"] label,
[data-testid="stMainBlockContainer"] [data-testid="stSlider"] label {
  color: #dce7f5 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stFileUploaderDropzone"],
[data-testid="stMainBlockContainer"] [data-testid="stCameraInput"] {
  background: #101e30 !important;
  color: #dce7f5 !important;
  border-color: #4b6684 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stFileUploaderDropzone"] *,
[data-testid="stMainBlockContainer"] [data-testid="stCameraInput"] * {
  color: #dce7f5 !important;
}
[data-testid="stMainBlockContainer"] .stButton > button,
[data-testid="stMainBlockContainer"] [data-testid="stFormSubmitButton"] > button,
[data-testid="stMainBlockContainer"] .stDownloadButton > button,
[data-testid="stMainBlockContainer"] [data-testid="stDownloadButton"] button,
[data-testid="stMainBlockContainer"] .stLinkButton a,
[data-testid="stMainBlockContainer"] [data-testid="stPageLink"] a {
  background: #20334b !important;
  color: #f1f6fd !important;
  border: 1px solid #48617e !important;
  -webkit-text-fill-color: #f1f6fd !important;
  box-shadow: none !important;
}
[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"],
[data-testid="stMainBlockContainer"] [data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: linear-gradient(110deg, #126d77, #2457a7) !important;
  color: #ffffff !important;
  border-color: #3b8caa !important;
}
[data-testid="stMainBlockContainer"] .stButton > button:disabled,
[data-testid="stMainBlockContainer"] .stDownloadButton > button:disabled {
  background: #182638 !important;
  color: #8396ad !important;
  border-color: #2d4057 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stDataFrame"],
[data-testid="stMainBlockContainer"] [data-testid="stDataEditor"],
[data-testid="stMainBlockContainer"] [data-testid="stTable"] {
  background: #111e2e !important;
  border-color: #33465d !important;
  color: #e7eef8 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] p {
  color: #aebfd3 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] {
  color: #f3f7ff !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stAlert"] {
  background: #152235 !important;
  color: #e7eef8 !important;
  border-color: #405670 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stAlert"] * {
  color: #e7eef8 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important;
  border-color: #33465d !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stTabs"] [data-baseweb="tab"] {
  color: #afc0d5 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stTabs"] [aria-selected="true"] {
  color: #9fc5ff !important;
  border-bottom-color: #69a4ff !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] summary,
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] summary * {
  color: #e7eef8 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
  color: #dce7f5 !important;
}
[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[data-baseweb="option"],
[data-baseweb="calendar"],
[data-baseweb="calendar"] * {
  background-color: #152235 !important;
  color: #e7eef8 !important;
  border-color: #405670 !important;
}
[data-baseweb="option"]:hover,
[role="option"][aria-selected="true"] {
  background: #29415f !important;
  color: #ffffff !important;
}
[data-testid="stHeader"] { background: rgba(11,20,33,.98) !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { color: #dce7f5 !important; }
[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] h4,
[data-testid="stMainBlockContainer"] h5,
[data-testid="stMainBlockContainer"] [data-testid="stHeading"] * {
  color: #f4f8ff !important;
  opacity: 1 !important;
}
[data-testid="stMainBlockContainer"] h1 {
  font-size: clamp(1.8rem, 2.4vw, 2.35rem) !important;
  font-weight: 800 !important;
  border-bottom: 2px solid #4269a8 !important;
  padding-bottom: .45rem !important;
}
[data-testid="stMainBlockContainer"] h2 {
  font-weight: 760 !important;
  border-left: 4px solid #79aaff !important;
  padding-left: .65rem !important;
}
[data-testid="stMainBlockContainer"] h3 { color: #c5dcff !important; font-weight: 730 !important; }
[data-testid="stMainBlockContainer"] .resq-title { border: 0 !important; padding: 0 !important; }
[data-testid="stMainBlockContainer"] .resq-header {
  background: linear-gradient(120deg, #11253b, #124a53 62%, #183a59) !important;
  border-color: #31536b !important;
}
[data-testid="stMainBlockContainer"] .resq-header * { color: #f4f8ff !important; }
[data-testid="stMainBlockContainer"] .resq-header .resq-sub { color: #c5d5e8 !important; }
[data-testid="stMainBlockContainer"] .resq-map-frame {
  background: #152235 !important; color: #e7eef8 !important; border-color: #405670 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stVegaLiteChart"],
[data-testid="stMainBlockContainer"] [data-testid="stPlotlyChart"],
[data-testid="stMainBlockContainer"] [data-testid="stPyplot"],
[data-testid="stMainBlockContainer"] [data-testid="stDeckGlJsonChart"] {
  background: #111e2e !important;
  border: 1px solid #33465d !important;
  border-radius: 14px !important;
  overflow: hidden !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stPlotlyChart"] iframe {
  color-scheme: dark !important;
}



/* Incident form dark-mode repair: override the light form panel and low-contrast labels. */
[data-testid="stMainBlockContainer"] [data-testid="stForm"] {
  background: #111e2e !important;
  background-color: #111e2e !important;
  border: 1px solid #334b65 !important;
  color: #e7eef8 !important;
  color-scheme: dark !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] label,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-testid="stWidgetLabel"],
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-testid="stWidgetLabel"] *,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-testid="stMarkdownContainer"],
[data-testid="stMainBlockContainer"] [data-testid="stForm"] p {
  color: #dce7f5 !important;
  -webkit-text-fill-color: #dce7f5 !important;
  opacity: 1 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] input,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] textarea,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="input"],
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="textarea"],
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="select"] > div,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-testid="stNumberInput"] button {
  background: #0e1a2a !important;
  background-color: #0e1a2a !important;
  color: #f1f6fd !important;
  -webkit-text-fill-color: #f1f6fd !important;
  border-color: #405670 !important;
  box-shadow: none !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-testid="stFileUploaderDropzone"],
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-testid="stFileUploaderDropzone"] section {
  background: #101e30 !important;
  color: #dce7f5 !important;
  border-color: #4b6684 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-testid="stFileUploaderDropzone"] * {
  color: #dce7f5 !important;
  -webkit-text-fill-color: #dce7f5 !important;
}

/* Dark-mode contrast pass: navigation rail, empty tables and chat widgets. */
:root { color-scheme: dark !important; }
[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
  background: #0d1928 !important;
  color: #e8f0fb !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] small {
  color: #dce7f5 !important;
  -webkit-text-fill-color: #dce7f5 !important;
  opacity: 1 !important;
}
[data-testid="stSidebar"] .rx-sidebar-brand,
[data-testid="stSidebar"] .rx-brand-name,
[data-testid="stSidebar"] .rx-brand-tag,
[data-testid="stSidebar"] .rx-brand-status,
[data-testid="stSidebar"] .rx-sidebar-brand * {
  color: #eaf4ff !important;
  -webkit-text-fill-color: #eaf4ff !important;
}
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNav"] a *,
[data-testid="stSidebarNav"] [aria-current="page"],
[data-testid="stSidebarNav"] [aria-current="page"] * {
  color: #eaf4ff !important;
  -webkit-text-fill-color: #eaf4ff !important;
  opacity: 1 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stTable"],
[data-testid="stMainBlockContainer"] [data-testid="stDataFrame"],
[data-testid="stMainBlockContainer"] [data-testid="stDataEditor"],
[data-testid="stMainBlockContainer"] [data-testid="stTable"] table,
[data-testid="stMainBlockContainer"] [data-testid="stTable"] thead,
[data-testid="stMainBlockContainer"] [data-testid="stTable"] tbody,
[data-testid="stMainBlockContainer"] [data-testid="stTable"] tr,
[data-testid="stMainBlockContainer"] [data-testid="stTable"] th,
[data-testid="stMainBlockContainer"] [data-testid="stTable"] td {
  background: #111e2e !important;
  background-color: #111e2e !important;
  color: #e7eef8 !important;
  -webkit-text-fill-color: #e7eef8 !important;
  border-color: #33465d !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stTable"] tbody tr:nth-child(even),
[data-testid="stMainBlockContainer"] [data-testid="stDataFrame"] [role="row"]:nth-child(even) {
  background: #17263a !important;
  background-color: #17263a !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stTable"] td *,
[data-testid="stMainBlockContainer"] [data-testid="stTable"] th * {
  color: #e7eef8 !important;
  -webkit-text-fill-color: #e7eef8 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stChatInput"],
[data-testid="stMainBlockContainer"] [data-testid="stChatInput"] > div,
[data-testid="stMainBlockContainer"] [data-testid="stChatInput"] textarea,
[data-testid="stMainBlockContainer"] [data-testid="stChatInput"] [data-baseweb="textarea"] {
  background: #111e2e !important;
  background-color: #111e2e !important;
  color: #f1f6fd !important;
  -webkit-text-fill-color: #f1f6fd !important;
  border-color: #405670 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stChatInput"] textarea::placeholder {
  color: #a8bad0 !important;
  -webkit-text-fill-color: #a8bad0 !important;
  opacity: 1 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] label,
[data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"],
[data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] *,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] li,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] strong {
  color: #e2ebf7 !important;
  -webkit-text-fill-color: #e2ebf7 !important;
  opacity: 1 !important;
}

/* Accessible custom page navigation and dark workspace polish. */
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  display: flex !important;
  align-items: center !important;
  min-height: 42px !important;
  padding: .65rem .8rem !important;
  margin: 3px 0 !important;
  border: 1px solid transparent !important;
  border-radius: 11px !important;
  color: #d4e3f4 !important;
  background: transparent !important;
  text-decoration: none !important;
  font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
  color: #f3fffe !important;
  background: #1b3448 !important;
  border-color: #36586b !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:focus-visible {
  outline: 2px solid #5eead4 !important;
  outline-offset: 2px !important;
}
[data-testid="stSidebar"] h4 {
  color: #9fb8d0 !important;
  font-size: .72rem !important;
  letter-spacing: .12em !important;
  text-transform: uppercase !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stPlotlyChart"],
[data-testid="stMainBlockContainer"] [data-testid="stVegaLiteChart"],
[data-testid="stMainBlockContainer"] [data-testid="stDataFrame"],
[data-testid="stMainBlockContainer"] [data-testid="stDataEditor"],
[data-testid="stMainBlockContainer"] [data-testid="stTable"] {
  border: 1px solid #33465d !important;
  border-radius: 14px !important;
  background: #111e2e !important;
  color: #e7eef8 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMainBlockContainer"] [data-testid="stExpander"],
[data-testid="stMainBlockContainer"] [data-testid="stMetric"] {
  border: 1px solid #33465d !important;
  border-radius: 15px !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] li,
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"],
[data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] {
  color: #dce7f5 !important;
}
[data-testid="stMainBlockContainer"] :is(input, textarea):focus,
[data-testid="stMainBlockContainer"] [data-baseweb="select"]:focus-within {
  border-color: #5eead4 !important;
  box-shadow: 0 0 0 3px rgba(94,234,212,.14) !important;
}

/* Sidebar dark-mode repair: brand card, AI-mode badge, and nav labels. */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  background: #0b1726 !important;
  color: #e8f1fc !important;
}
section[data-testid="stSidebar"] .rx-sidebar-brand {
  background: linear-gradient(135deg, #142b40 0%, #15283c 68%, #102338 100%) !important;
  border: 1px solid #34516a !important;
  box-shadow: 0 8px 22px rgba(0,0,0,.22) !important;
  color: #f0f6ff !important;
}
section[data-testid="stSidebar"] .rx-brand-name {
  color: #f4f8ff !important;
  -webkit-text-fill-color: #f4f8ff !important;
  font-weight: 750 !important;
}
section[data-testid="stSidebar"] .rx-brand-tag,
section[data-testid="stSidebar"] .rx-brand-status {
  color: #b7c9dd !important;
  -webkit-text-fill-color: #b7c9dd !important;
  opacity: 1 !important;
}
section[data-testid="stSidebar"] .rx-brand-line {
  background: #314a61 !important;
}
section[data-testid="stSidebar"] .rx-brand-mark {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
  display: inline-block !important;
  background: #1b3045 !important;
  border: 1px solid #3c566f !important;
  border-radius: 9px !important;
  color: #e8f2ff !important;
  -webkit-text-fill-color: #e8f2ff !important;
  padding: .45rem .65rem !important;
  font-weight: 650 !important;
  opacity: 1 !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p {
  color: #d7e4f3 !important;
  -webkit-text-fill-color: #d7e4f3 !important;
  opacity: 1 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
  color: #dce9f8 !important;
  -webkit-text-fill-color: #dce9f8 !important;
  background: transparent !important;
  border-color: transparent !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
  background: #1a2c40 !important;
  border-color: #34516a !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] * {
  background: linear-gradient(100deg, #087f9f 0%, #0876b5 100%) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  opacity: 1 !important;
}
section[data-testid="stSidebar"] hr {
  border-color: #30465b !important;
}
</style>
"""



ENHANCED_CSS = """
<style>
/* Compact operations label in the main header's upper-left corner. */

[data-testid="stSidebarNav"] > ul {
  gap: .18rem;
}
[data-testid="stSidebarNav"] a {
  min-height: 2.7rem;
  display: flex;
  align-items: center;
  font-size: .91rem;
  letter-spacing: -.01em;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
  box-shadow: inset 0 0 0 1px rgba(20,184,166,.13);
}
[data-testid="stSidebarNav"] a[aria-current="page"]::before {
  content: "";
  width: 5px;
  height: 5px;
  flex: 0 0 5px;
  border-radius: 50%;
  margin-right: .55rem;
  background: #0d9488;
  box-shadow: 0 0 0 3px rgba(13,148,136,.12);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
  font-size: 1.02rem !important;
  letter-spacing: .08em !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  font-size: .84rem;
  line-height: 1.45;
}
[data-testid="stMainBlockContainer"] {
  padding-top: 1rem !important;
}
.resq-header {
  padding: 21px 24px 20px;
  margin: 3px 0 20px;
  border-radius: 13px;
  box-shadow: 0 5px 16px rgba(12,34,56,.08);
  background: linear-gradient(112deg, #13283d 0%, #174b52 58%, #183b57 100%);
}
.resq-header::after {
  width: 210px;
  height: 210px;
  right: -82px;
  top: -130px;
  box-shadow: 0 0 0 24px rgba(94,234,212,.035), 0 0 0 48px rgba(94,234,212,.025);
}
.resq-title {
  font-size: clamp(23px, 2vw, 31px) !important;
  max-width: 760px;
  line-height: 1.12 !important;
}
.resq-sub {
  font-size: 13px;
  max-width: 700px;
}
.resq-pills {
  position: relative;
  z-index: 1;
}
.metric-card, div[data-testid="stMetric"], .panel {
  box-shadow: 0 2px 8px rgba(15,36,61,.035);
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  transform: translateY(-1px);
}
/* No page-entry animation: avoid the visible fade/unstyled flash on navigation. */
[data-testid="stMainBlockContainer"] > div {
  animation: none !important;
}
[data-testid="stSidebarNav"] a,
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  transition: background-color .16s ease, color .16s ease, border-color .16s ease, transform .16s ease;
}
@media (max-width: 850px) {
  [data-testid="stMainBlockContainer"] { padding-top: .65rem !important; }
  .resq-header { padding: 17px 15px; margin-bottom: 15px; }
  .resq-title { font-size: 23px !important; }
  .resq-pills { gap: 6px; }
  .pill { white-space: normal; }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stMainBlockContainer"] > div { animation: none !important; }
}
/* RescueX visual refresh: stronger colour, depth and interaction */
:root {
  --rx-accent: #14b8a6;
  --rx-accent-2: #38bdf8;
  --rx-warm: #f59e0b;
  --rx-critical: #f43f5e;
}
[data-testid="stMainBlockContainer"] {
  max-width: 1720px;
  padding-left: clamp(1rem, 2.4vw, 2.5rem);
  padding-right: clamp(1rem, 2.4vw, 2.5rem);
}
.stApp {
  background:
    radial-gradient(ellipse at 8% 0%, rgba(20,184,166,.08), transparent 30%),
    radial-gradient(ellipse at 92% 5%, rgba(56,189,248,.08), transparent 28%),
    var(--resq-canvas);
}
.resq-header {
  position: relative;
  overflow: hidden;
  padding: 25px 26px 24px;
  border: 1px solid rgba(56,189,248,.22);
  border-radius: 20px;
  background: linear-gradient(120deg, rgba(15,36,61,.98), rgba(15,76,87,.96) 62%, rgba(21,57,91,.98));
  box-shadow: 0 14px 36px rgba(12,34,56,.14);
  margin: 8px 0 24px;
}
.resq-header::after {
  content: "";
  position: absolute;
  width: 260px;
  height: 260px;
  right: -75px;
  top: -145px;
  border: 1px solid rgba(94,234,212,.35);
  border-radius: 50%;
  box-shadow: 0 0 0 28px rgba(94,234,212,.045), 0 0 0 58px rgba(94,234,212,.035);
  pointer-events: none;
}
.resq-header .resq-kicker { color: #5eead4; }
.resq-header .resq-title { color: #f8fafc !important; letter-spacing: -.04em; }
.resq-header .resq-sub { color: #c4d5e7 !important; }
.resq-header .pill { background: rgba(255,255,255,.09); color: #e7f1fb; border-color: rgba(255,255,255,.18); }
.resq-header .pill.ok { background: rgba(16,185,129,.15); color: #a7f3d0; border-color: rgba(52,211,153,.4); }
.resq-header .pill.warn { background: rgba(245,158,11,.14); color: #fde68a; border-color: rgba(245,158,11,.38); }
.resq-header .pill.bad { background: rgba(244,63,94,.15); color: #fecdd3; border-color: rgba(251,113,133,.4); }
.metric-card, div[data-testid="stMetric"] {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  border-color: color-mix(in srgb, var(--resq-border) 78%, var(--rx-accent));
  box-shadow: 0 8px 24px rgba(15,36,61,.055);
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.metric-card::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: linear-gradient(180deg, var(--rx-accent), var(--rx-accent-2));
}
.metric-card.critical::before { background: linear-gradient(180deg, #fb7185, #e11d48); }
.metric-card.medical::before { background: linear-gradient(180deg, #fbbf24, #f97316); }
.metric-card:hover, div[data-testid="stMetric"]:hover {
  transform: translateY(-3px);
  border-color: var(--rx-accent);
  box-shadow: 0 14px 30px rgba(15,36,61,.12);
}
.metric-card .value { letter-spacing: -.04em; }
.panel {
  border-radius: 17px;
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.panel:hover {
  transform: translateY(-2px);
  border-color: rgba(20,184,166,.55);
  box-shadow: 0 12px 28px rgba(15,36,61,.09);
}
.stButton > button, [data-testid="stFormSubmitButton"] > button,
.stDownloadButton > button, .stLinkButton > a {
  min-height: 2.65rem;
  border-radius: 11px;
  transition: transform .16s ease, box-shadow .16s ease, filter .16s ease;
}
.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: linear-gradient(110deg, #0f766e, #0e7490);
  border-color: #0f766e;
  box-shadow: 0 5px 14px rgba(15,118,110,.18);
}
.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
  filter: brightness(1.08);
  box-shadow: 0 8px 20px rgba(15,118,110,.25);
}
[data-testid="stSidebar"] {
  box-shadow: 5px 0 24px rgba(15,36,61,.035);
}
[data-testid="stSidebarNav"] a {
  padding: .55rem .7rem;
  border-radius: 11px;
  transition: background .18s ease, transform .18s ease;
}
[data-testid="stSidebarNav"] a:hover {
  background: rgba(20,184,166,.10) !important;
  transform: translateX(2px);
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
  background: linear-gradient(100deg, rgba(20,184,166,.16), rgba(56,189,248,.10)) !important;
  border-left: 3px solid var(--rx-accent);
}
[data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 15px;
  transition: border-color .18s ease, box-shadow .18s ease;
}
[data-testid="stExpander"]:hover {
  border-color: rgba(20,184,166,.45);
}
[data-testid="stDataFrame"] {
  border-radius: 14px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  transition: background .16s ease, color .16s ease;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  background: rgba(20,184,166,.08);
}
[data-testid="stAlert"] {
  border-radius: 13px;
}
@keyframes rx-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(20,184,166,.16); }
  50% { box-shadow: 0 0 0 5px rgba(20,184,166,0); }
}
.resq-header .pill.ok { animation: rx-pulse 3s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
    transform: none !important;
  }
}
@media (max-width: 850px) {
  .resq-header { padding: 20px 17px; border-radius: 15px; }
  .metric-card { padding: 14px 12px; }
}

/* High-contrast RescueX command navigation — intentionally visible in both themes. */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b1727 0%, #10253a 55%, #0d1d30 100%) !important;
  border-right: 1px solid rgba(94,234,212,.18) !important;
  box-shadow: 8px 0 28px rgba(3,12,24,.10) !important;
}
section[data-testid="stSidebar"] > div { padding: 1.05rem .8rem 1.5rem; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
  color: #c2d1e2 !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 { color: #f4fbff !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(173,198,222,.18) !important; }
[data-testid="stSidebarNav"] { padding: .5rem 0 1rem; }
[data-testid="stSidebarNav"] a {
  color: #c7d7e8 !important;
  margin: 3px 0 !important;
  padding: .68rem .75rem !important;
  border: 1px solid transparent !important;
  border-radius: 12px !important;
  min-height: 2.8rem;
}
[data-testid="stSidebarNav"] a:hover {
  color: #f3fffe !important;
  background: rgba(45,212,191,.12) !important;
  border-color: rgba(94,234,212,.18) !important;
  transform: translateX(3px);
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
  color: #f4fffd !important;
  background: linear-gradient(100deg, rgba(13,148,136,.34), rgba(56,189,248,.12)) !important;
  border: 1px solid rgba(94,234,212,.26) !important;
  border-left: 3px solid #5eead4 !important;
  box-shadow: inset 0 0 20px rgba(45,212,191,.045);
}
.rx-sidebar-brand {
  padding: 16px 13px 15px;
  margin: 0 0 14px;
  border: 1px solid rgba(94,234,212,.22);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(20,184,166,.15), rgba(56,189,248,.07));
}
.rx-brand-row { display:flex; align-items:center; gap:10px; }
.rx-brand-mark {
  width:38px; height:38px; display:flex; align-items:center; justify-content:center;
  border-radius:12px; background:linear-gradient(135deg,#14b8a6,#0284c7);
  color:#f0fdfa; font-size:20px; font-weight:800;
  box-shadow:0 6px 18px rgba(20,184,166,.22);
}
.rx-brand-name { color:#f4fbff; font-size:19px; line-height:1.1; font-weight:800; letter-spacing:-.045em; }
.rx-brand-tag { color:#91a9c2; font-size:9px; font-weight:700; letter-spacing:.16em; margin-top:5px; }
.rx-brand-line { height:1px; background:rgba(173,198,222,.15); margin:13px 0 10px; }
.rx-brand-status { display:flex; align-items:center; gap:7px; color:#a9c0d5; font-size:10px; font-weight:700; letter-spacing:.08em; }
.rx-status-dot { width:7px; height:7px; border-radius:50%; background:#34d399; box-shadow:0 0 0 4px rgba(52,211,153,.10); }
.rx-sidebar-note { padding:10px 11px; border:1px solid rgba(173,198,222,.13); border-radius:11px; background:rgba(255,255,255,.035); }
.resq-header { min-height: 176px; }
.resq-kicker { display:flex; align-items:center; gap:8px; }
.resq-kicker::before { content:""; width:22px; height:2px; border-radius:3px; background:#5eead4; }
[data-testid="stMainBlockContainer"] h2 { margin-top:1.25rem; }
[data-testid="stMainBlockContainer"] [data-testid="stMetric"] { min-height:112px; }
[data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] { letter-spacing:-.045em; }
[data-testid="stMainBlockContainer"] [data-testid="stForm"] {
  border:1px solid var(--resq-border); border-radius:16px; padding:20px;
  background:var(--resq-panel); box-shadow:0 8px 24px rgba(15,36,61,.045);
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] label { font-weight:600; }
[data-testid="stMainBlockContainer"] [data-testid="stFileUploaderDropzone"] {
  border:1px dashed #7b9bb4; border-radius:13px; background:rgba(20,184,166,.035);
}
[data-testid="stMainBlockContainer"] [data-testid="stDataFrame"] { border:1px solid var(--resq-border); }
@media (prefers-reduced-motion: reduce) {
  [data-testid="stSidebarNav"] a { transition:none !important; }
  [data-testid="stSidebarNav"] a:hover { transform:none !important; }
}
</style>
"""


POLISH_CSS = """
<style>
/* Cohesive operations-console redesign: rich navigation rail, brighter workspace. */
:root {
  --rx-rail: #091827;
  --rx-rail-2: #102b40;
  --rx-mint: #34d399;
  --rx-sky: #38bdf8;
}
section[data-testid="stSidebar"] {
  background:
    radial-gradient(ellipse at 12% 0%, rgba(20,184,166,.19), transparent 42%),
    linear-gradient(165deg, #081624 0%, #102a40 58%, #0b1c2e 100%) !important;
  border-right: 1px solid rgba(94,234,212,.28) !important;
  box-shadow: 10px 0 34px rgba(4,15,28,.13) !important;
}
section[data-testid="stSidebar"] > div {
  padding: 1.15rem .85rem 1.6rem !important;
}
.rx-sidebar-brand {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(20,184,166,.19), rgba(56,189,248,.09) 70%, rgba(255,255,255,.025)) !important;
  border-color: rgba(94,234,212,.32) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.045), 0 12px 28px rgba(0,0,0,.12);
}
.rx-sidebar-brand::after {
  content: "";
  position: absolute;
  width: 100px; height: 100px;
  right: -54px; top: -52px;
  border: 1px solid rgba(94,234,212,.25);
  border-radius: 50%;
  box-shadow: 0 0 0 14px rgba(94,234,212,.035), 0 0 0 28px rgba(94,234,212,.025);
  pointer-events: none;
}
.rx-brand-mark {
  background: linear-gradient(145deg, #2dd4bf, #0284c7) !important;
  box-shadow: 0 0 0 4px rgba(45,212,191,.09), 0 8px 22px rgba(20,184,166,.25) !important;
}
.rx-brand-name { letter-spacing: -.055em !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
  display: inline-block;
  padding: 7px 10px;
  border: 1px solid rgba(94,234,212,.16);
  border-radius: 9px;
  background: rgba(255,255,255,.045);
  color: #c8fff3 !important;
  font-size: 11px;
  letter-spacing: .04em;
}
[data-testid="stSidebarNav"] { margin-top: .25rem; }
[data-testid="stSidebarNav"] a {
  min-height: 44px !important;
  padding: .72rem .8rem !important;
  color: #b8cadd !important;
  border: 1px solid transparent !important;
  border-radius: 12px !important;
}
[data-testid="stSidebarNav"] a:hover {
  color: #f0fdfa !important;
  background: linear-gradient(100deg, rgba(20,184,166,.18), rgba(56,189,248,.08)) !important;
  border-color: rgba(94,234,212,.22) !important;
  transform: translateX(3px);
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
  color: #f0fdfa !important;
  background: linear-gradient(100deg, rgba(13,148,136,.34), rgba(56,189,248,.15)) !important;
  border: 1px solid rgba(94,234,212,.3) !important;
  border-left: 3px solid #5eead4 !important;
  box-shadow: 0 5px 18px rgba(0,0,0,.1), inset 0 0 20px rgba(45,212,191,.04);
}
[data-testid="stSidebar"] hr { border-color: rgba(173,198,222,.18) !important; }
/* Search should look intentional before hover, not like an unstyled white input. */
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) [data-baseweb="input"] {
  min-height: 48px;
  background: linear-gradient(110deg, #102a40, #153b50) !important;
  border: 1px solid rgba(20,184,166,.55) !important;
  border-radius: 13px !important;
  box-shadow: 0 5px 18px rgba(15,36,61,.09), inset 0 1px 0 rgba(255,255,255,.04) !important;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease !important;
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) input {
  color: #f0fdfa !important;
  background: transparent !important;
  caret-color: #5eead4;
  font-weight: 550;
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) input::placeholder {
  color: #9bb9cc !important;
  opacity: 1 !important;
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) [data-baseweb="input"]:focus-within {
  border-color: #5eead4 !important;
  box-shadow: 0 0 0 3px rgba(45,212,191,.16), 0 10px 24px rgba(15,36,61,.12) !important;
  transform: translateY(-1px);
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) label {
  color: var(--resq-ink) !important;
  font-weight: 700 !important;
}
/* Keep the main workspace clearly distinct from the dark navigation rail. */
.stApp {
  background:
    radial-gradient(ellipse at 2% 0%, rgba(20,184,166,.075), transparent 28%),
    radial-gradient(ellipse at 100% 10%, rgba(56,189,248,.07), transparent 27%),
    var(--resq-canvas) !important;
}
[data-testid="stMainBlockContainer"] {
  padding-top: 1.15rem !important;
}
.resq-header {
  border-radius: 20px !important;
  box-shadow: 0 16px 38px rgba(8,27,46,.16), inset 0 1px 0 rgba(255,255,255,.06) !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stMetric"],
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] {
  border-radius: 16px !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stDataFrame"] {
  border-radius: 14px !important;
  box-shadow: 0 8px 24px rgba(15,36,61,.06);
}
[data-testid="stMainBlockContainer"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {
  min-height: 43px;
  border-color: #cbd8e5 !important;
  box-shadow: 0 2px 8px rgba(15,36,61,.035);
}
[data-testid="stMainBlockContainer"] [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
  border-color: #0f9e91 !important;
  box-shadow: 0 0 0 3px rgba(20,184,166,.12) !important;
}
@media (prefers-reduced-motion: reduce) {
  section[data-testid="stSidebar"] *, [data-testid="stMainBlockContainer"] * {
    transition-duration: .01ms !important;
    animation-duration: .01ms !important;
  }
}

/* Balanced slate-and-teal palette: sidebar and workspace sit at similar visual weight. */
:root {
  --resq-ink: #203548;
  --resq-muted: #607487;
  --resq-border: #d2dfe7;
  --resq-panel: #f9fcfd;
  --resq-canvas: #eaf1f5;
  --resq-blue: #176b78;
  --resq-teal: #138b83;
}
.stApp {
  background: linear-gradient(135deg, #e8f0f4 0%, #edf3f6 54%, #e5eef3 100%) !important;
}
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #d0e0e8 0%, #d8e5eb 52%, #cbdde6 100%) !important;
  border-right: 1px solid #b6ccd8 !important;
  box-shadow: 5px 0 22px rgba(25,58,78,.09) !important;
}
section[data-testid="stSidebar"] > div {
  background: transparent !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
  color: #17394b !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: #405f72 !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
  color: #496477 !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
  background: #eef5f7 !important;
  border-color: #c8dce4 !important;
  color: #235d68 !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 { color: #203b4e !important; }
section[data-testid="stSidebar"] hr { border-color: #c8d8e1 !important; }
.rx-sidebar-brand {
  background: linear-gradient(135deg, #d2e9e8, #dcecf4 72%, #e6f0f4) !important;
  border-color: #b8d8dc !important;
  box-shadow: 0 6px 16px rgba(31,75,89,.06) !important;
}
.rx-brand-name { color: #17394b !important; }
.rx-brand-tag, .rx-brand-status { color: #527183 !important; }
.rx-brand-line { background: #bfd4dd !important; }
.rx-status-dot { background: #0f9b83 !important; box-shadow: 0 0 0 4px rgba(15,155,131,.12) !important; }
.rx-brand-mark { box-shadow: 0 5px 14px rgba(20,120,135,.15) !important; }
[data-testid="stSidebarNav"] a {
  color: #39566a !important;
  border-color: transparent !important;
}
[data-testid="stSidebarNav"] a:hover {
  color: #164f5c !important;
  background: #d0e5e8 !important;
  border-color: #bddadd !important;
}
[data-testid="stSidebarNav"] a {
  min-height: 2.85rem !important;
  border-radius: 11px !important;
  margin: 4px 5px !important;
  padding: .55rem .75rem !important;
  color: #294b60 !important;
  font-weight: 600 !important;
  transition: background-color .14s ease, color .14s ease, border-color .14s ease !important;
}
[data-testid="stSidebarNav"] a:hover {
  color: #123f4f !important;
  background: #c1d9e3 !important;
  border-color: #a9c8d6 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
  color: #f4fbfd !important;
  background: linear-gradient(105deg, #236b78, #2b7f87) !important;
  border: 1px solid #1f6875 !important;
  border-left: 3px solid #45d2c1 !important;
  box-shadow: 0 5px 13px rgba(24,83,99,.16) !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"]::before {
  background: #7ce7db !important;
  box-shadow: 0 0 0 3px rgba(124,231,219,.18) !important;
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) [data-baseweb="input"] {
  background: #f6fbfc !important;
  border: 1px solid #b7d1dc !important;
  box-shadow: 0 2px 8px rgba(31,58,78,.045) !important;
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) input {
  color: #203548 !important;
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) input::placeholder {
  color: #71899a !important;
}
div[data-testid="stTextInput"]:has(input[placeholder*="Search"]) [data-baseweb="input"]:focus-within {
  border-color: #15988e !important;
  box-shadow: 0 0 0 3px rgba(21,152,142,.13) !important;
}
.resq-header {
  box-shadow: 0 10px 26px rgba(24,54,75,.10) !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stMetric"],
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMainBlockContainer"] [data-testid="stExpander"] {
  box-shadow: 0 4px 15px rgba(31,58,78,.045) !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] {
  background: #f7fafc !important;
  border-color: #d1dfe7 !important;
  box-shadow: 0 8px 22px rgba(31,58,78,.055) !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] label {
  color: #304d60 !important;
  font-weight: 650 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] input,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] textarea,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="select"] > div {
  background: #ffffff !important;
  border-color: #c4d6e0 !important;
  color: #203548 !important;
  border-radius: 10px !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stForm"] input:focus,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] textarea:focus,
[data-testid="stMainBlockContainer"] [data-testid="stForm"] [data-baseweb="select"]:focus-within {
  border-color: #15988e !important;
  box-shadow: 0 0 0 3px rgba(21,152,142,.11) !important;
}
/* Disable all UI motion to prevent distracting transitions during Streamlit page navigation. */
.stApp *, .stApp *::before, .stApp *::after {
  animation: none !important;
  transition: none !important;
  scroll-behavior: auto !important;
  transform: none !important;
}

/* Keep the selected page label readable on the blue/cyan active navigation pill. */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] *,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"]::after {
  color: #ffffff !important;
  font-weight: 700 !important;
  font-size: .91rem !important;
  opacity: 1 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
  background: linear-gradient(100deg, #0f9fbd 0%, #0284c7 100%) !important;
  border-color: rgba(125,211,252,.7) !important;
  border-left: 3px solid #7dd3fc !important;
}
</style>
"""


def inject_theme() -> None:
    # Keep the selected theme in the URL so it survives a browser refresh
    # and navigation between Streamlit pages. Session state alone is reset
    # when the app is reloaded.
    st.session_state["resq_theme"] = "Light"
    try:
        if "theme" in st.query_params:
            del st.query_params["theme"]
    except Exception:
        pass

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(ENHANCED_CSS, unsafe_allow_html=True)
    st.markdown(POLISH_CSS, unsafe_allow_html=True)


def page_setup(title: str) -> None:
    st.set_page_config(
        page_title=f"ResQ-AI | {title}",
        page_icon="🆘",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()


def render_sidebar(center: CommandCenter) -> None:
    st.sidebar.markdown(
        """
        <div class="rx-sidebar-brand">
          <div class="rx-brand-row">
            <div class="rx-brand-mark">R</div>
            <div>
              <div class="rx-brand-name">ResQ-AI</div>
              <div class="rx-brand-tag">DISASTER INTELLIGENCE</div>
            </div>
          </div>
          <div class="rx-brand-line"></div>
          <div class="rx-brand-status"><span class="rx-status-dot"></span> COMMAND SYSTEM · ONLINE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(f"**{center.ai_mode}**")
    st.sidebar.markdown("#### COMMAND NAVIGATION")
    nav_items = [
        ("app.py", "⌂", "Command Center"),
        ("pages/2_Report_Incident.py", "＋", "Report Incident"),
        ("pages/4_Scenario_Simulator.py", "◈", "Scenario Simulator"),
        ("pages/7_Live_Government_Alerts.py", "◉", "Live Government Alerts"),
        ("pages/8_Incident_Operations.py", "⇄", "Incident Operations"),
        ("pages/9_Situation_Reports.py", "▤", "Situation Reports"),
    ]
    for page_path, glyph, label in nav_items:
        st.sidebar.page_link(page_path, label=f"{glyph}  {label}")
    st.sidebar.divider()
    st.sidebar.caption(DISCLAIMER)

    if llm_configured():
        st.sidebar.caption("AI analysis: model connection configured")
    else:
        pass  # No LLM-status notice in the sidebar.


def render_header(center: CommandCenter, subtitle: str) -> None:
    ai_class = "ok" if "Active" in center.ai_mode else "warn"
    from pathlib import Path

    icon_path = Path(__file__).resolve().parents[1] / "assets" / "resq-chatbot-icon.png"
    st.markdown(
        """
        <style>
        div[data-testid="stPopover"] { position: fixed !important; left: 1rem !important; bottom: 1rem !important; z-index: 1000002 !important; }
        div[data-testid="stPopover"] > button { width: 74px !important; height: 74px !important; border-radius: 50% !important; border: 0 !important; padding: 0 !important; background: #399ed8 !important; box-shadow: 0 8px 22px rgba(15,23,42,.32) !important; }
        div[data-testid="stPopover"] > button > div { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.popover("💬", help="Open ResQ Assistant chat"):
        st.image(str(icon_path), width=56)
        from components.chatbot import render_chatbot
        render_chatbot(center)
    st.markdown(
        f"""
        <div class="resq-header">
          <div>
            <div class="resq-kicker">RESCUEX · LIVE INTELLIGENCE</div>
            <h1 class="resq-title">INTELLIGENT DISASTER COMMAND CENTER</h1>
            <div class="resq-sub">{subtitle}</div>
          </div>
          <div class="resq-pills">
            <div class="pill {ai_class}">{center.ai_mode}</div>
            <div class="pill ok">SYSTEM STATUS: OPERATIONAL</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
