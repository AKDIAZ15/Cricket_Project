import os
import time

import requests
import streamlit as st

BASE_URL = os.getenv("API_BASE_URL", "http://cricket-api:5000")

st.set_page_config(
    page_title="Cricket World Cup  Board",
    page_icon="🏏",
    layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 1.5rem;
    }

    .hero {
        background: linear-gradient(135deg, #0f5132 0%, #1b7f5a 52%, #d6a329 100%);
        color: white;
        padding: 24px 28px;
        border-radius: 8px;
        margin-bottom: 18px;
        box-shadow: 0 10px 28px rgba(15, 81, 50, 0.18);
    }

    .hero h1 {
        margin: 0;
        font-size: 42px;
        font-weight: 800;
        letter-spacing: 0;
    }

    .hero p {
        margin: 8px 0 0;
        font-size: 16px;
        opacity: 0.92;
    }

    .section-title {
        font-size: 22px;
        font-weight: 750;
        margin: 22px 0 10px;
        color: #1f2933;
    }

    .soft-panel {
        border: 1px solid #e6e8eb;
        background: #ffffff;
        border-radius: 8px;
        padding: 18px 20px;
        min-height: 138px;
        box-shadow: 0 4px 14px rgba(31, 41, 51, 0.06);
    }

    .panel-label {
        color: #667085;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .team-name {
        font-size: 18px;
        font-weight: 700;
        color: #1f2933;
        margin: 6px 0;
    }

    .venue-name {
        font-size: 18px;
        font-weight: 700;
        color: #1f2933;
        line-height: 1.35;
        margin-top: 8px;
    }

    .score-strip {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 10px;
    }

    .score-pill {
        background: #f4f7f5;
        border: 1px solid #dce7df;
        border-radius: 8px;
        padding: 10px 12px;
        min-width: 118px;
    }

    .score-pill .value {
        color: #0f5132;
        font-size: 25px;
        font-weight: 800;
        line-height: 1.1;
    }

    .score-pill .label {
        color: #667085;
        font-size: 13px;
        margin-top: 2px;
    }

    .live-box {
        background: #101828;
        color: #f8fafc;
        border-radius: 8px;
        padding: 16px;
        min-height: 210px;
        white-space: pre-wrap;
        font-family: Consolas, monospace;
        font-size: 15px;
        line-height: 1.55;
    }

    div[data-testid="stMetricValue"] {
        color: #0f5132;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hero">
        <h1>🏏 Cricket World Cup Statistics</h1>
        <p>Match analytics, extras, wickets, player search, and live ball-by-ball simulation.</p>
    </div>
    """,
    unsafe_allow_html=True
)


def api_get(path):
    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException:
        st.error(
            "Flask API is not running. Start it first with: python app.py"
        )
        st.info(
            f"The dashboard is trying to connect to {BASE_URL}"
        )
        st.stop()


def render_panel(label, body):
    st.markdown(
        f"""
        <div class="soft-panel">
            <div class="panel-label">{label}</div>
            {body}
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# MATCH CONTROLS
# =========================

st.markdown(
    '<div class="section-title">🎯 Match Control Center</div>',
    unsafe_allow_html=True
)

years = api_get("/years")

control_col1, control_col2, control_col3 = st.columns([1, 2.4, 1])

with control_col1:
    year = st.selectbox(
        "📅 Select Year",
        years
    )

matches = api_get(f"/matches/{year}")

match_labels = [
    m["label"] for m in matches
]

with control_col2:
    selected_label = st.selectbox(
        "🏟️ Select Match",
        match_labels
    )

selected_match = None

for m in matches:
    if m["label"] == selected_label:
        selected_match = m["match_id"]

innings_list = api_get(f"/innings/{selected_match}")

with control_col3:
    innings = st.selectbox(
        "🎯 Select Innings",
        innings_list
    )

# =========================
# MATCH SUMMARY
# =========================

summary = api_get(f"/match_summary/{selected_match}")

st.markdown(
    '<div class="section-title">📋 Match Information</div>',
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns([1.25, 1.15, 1.35])

teams_html = "".join(
    f'<div class="team-name">🏏 {team}</div>'
    for team in summary["teams"]
)

with col1:
    render_panel("Teams", teams_html)

with col2:
    render_panel(
        "Venue",
        f'<div class="venue-name">📍 {summary["venue"]}</div>'
    )

with col3:
    render_panel(
        "Match Stats",
        f"""
        <div class="score-strip">
            <div class="score-pill">
                <div class="value">{summary["runs"]}</div>
                <div class="label">Total Runs</div>
            </div>
            <div class="score-pill">
                <div class="value">{summary["wickets"]}</div>
                <div class="label">Total Wickets</div>
            </div>
        </div>
        """
    )

# =========================
# EXTRAS PANEL
# =========================

extras = api_get(f"/extras/{selected_match}")

st.markdown(
    '<div class="section-title">🚨 Extras Summary</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("↔️ Wides", extras["wides"])
c2.metric("⚠️ No Balls", extras["noballs"])
c3.metric("🏃 Byes", extras["byes"])
c4.metric("🦵 Leg Byes", extras["legbyes"])

# =========================
# WICKET FILTER
# =========================

wicket_types = api_get(f"/wicket_types/{selected_match}")

filter_col, player_col = st.columns([1, 1.4])

with filter_col:
    st.markdown(
        '<div class="section-title">🎯 Wicket Filter</div>',
        unsafe_allow_html=True
    )

    selected_wicket = st.selectbox(
        "Choose wicket type",
        ["All"] + wicket_types
    )

    if selected_wicket != "All":
        wicket_players = api_get(
            f"/wicket_players/{selected_match}/{selected_wicket}"
        )

        st.subheader(
            f"🎯 {selected_wicket.upper()} Dismissals"
        )

        if wicket_players:
            st.table(wicket_players)
            st.metric(
                "Total Dismissals",
                len(wicket_players)
            )

        else:
            st.info("No dismissals found.")

# =========================
# PLAYER SEARCH
# =========================

with player_col:
    st.markdown(
        '<div class="section-title">🔎 Player Search</div>',
        unsafe_allow_html=True
    )

    player_name = st.text_input(
        "Enter player name (partial allowed)",
        placeholder="Example: McCullum"
    )

    if player_name:
        player_data = api_get(f"/player_search/{player_name}")

        st.write("### 🧾 Player Matches")
        st.table(player_data)

# =========================
# LIVE MATCH SCORE
# =========================

st.markdown(
    '<div class="section-title">📡 Live Match Score</div>',
    unsafe_allow_html=True
)

feed_placeholder = st.empty()

while True:
    try:
        data = requests.get(
            f"{BASE_URL}/live_feed/{selected_match}/{innings}",
            timeout=10
        ).json()

        if data:
            lines = [
                d["text"]
                for d in data
            ]

            live_text = "\n".join(lines[-20:])

        else:
            live_text = "⏳ Waiting for simulation...\n\nRun docker compose run --rm simulator and enter Match ID 335982, Innings 1."

        feed_placeholder.markdown(
            f'<div class="live-box">{live_text}</div>',
            unsafe_allow_html=True
        )

    except requests.exceptions.RequestException:
        feed_placeholder.markdown(
            '<div class="live-box">🔄 Live feed loading...</div>',
            unsafe_allow_html=True
        )

    time.sleep(1)
