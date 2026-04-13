import streamlit as st
import requests
import time

BASE_URL = "http://127.0.0.1:5000"

st.set_page_config(
    page_title="Cricket World Cup Dashboard",
    layout="wide"
)

st.title("🏏 Cricket World Cup Stats Dashboard")

# =========================
# YEAR SELECTION
# =========================

years = requests.get(
    f"{BASE_URL}/years"
).json()

year = st.selectbox(
    "📅 Select Year",
    years
)

# =========================
# MATCH SELECTION
# =========================

matches = requests.get(
    f"{BASE_URL}/matches/{year}"
).json()

match_labels = [
    m["label"] for m in matches
]

selected_label = st.selectbox(
    "🏟️ Select Match",
    match_labels
)

selected_match = None

for m in matches:

    if m["label"] == selected_label:
        selected_match = m["match_id"]

# =========================
# INNINGS SELECTION
# =========================

innings_list = requests.get(
    f"{BASE_URL}/innings/{selected_match}"
).json()

innings = st.selectbox(
    "🎯 Select Innings",
    innings_list
)

# =========================
# MATCH SUMMARY
# =========================

summary = requests.get(
    f"{BASE_URL}/match_summary/{selected_match}"
).json()

st.subheader("📋 Match Information")

col1, col2, col3 = st.columns(3)

with col1:

    st.write("### Teams")

    for t in summary["teams"]:
        st.write(t)

with col2:

    st.write("### Venue")
    st.write(summary["venue"])

with col3:

    st.write("### Match Stats")

    st.metric(
        "Total Runs",
        summary["runs"]
    )

    st.metric(
        "Total Wickets",
        summary["wickets"]
    )

# =========================
# EXTRAS PANEL
# =========================

extras = requests.get(
    f"{BASE_URL}/extras/{selected_match}"
).json()

st.subheader("🚨 Extras Summary")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Wides", extras["wides"])
c2.metric("No Balls", extras["noballs"])
c3.metric("Byes", extras["byes"])
c4.metric("Leg Byes", extras["legbyes"])

# =========================
# WICKET FILTER
# =========================

wicket_types = requests.get(
    f"{BASE_URL}/wicket_types/{selected_match}"
).json()

selected_wicket = st.selectbox(
    "🎯 Filter by Wicket Type",
    ["All"] + wicket_types
)

# =========================
# SHOW WICKET PLAYERS
# =========================

if selected_wicket != "All":

    wicket_players = requests.get(

        f"{BASE_URL}/wicket_players/"
        f"{selected_match}/"
        f"{selected_wicket}"

    ).json()

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

        st.write(
            "No dismissals found."
        )

# =========================
# PLAYER SEARCH
# =========================

st.subheader("🔍 Player Search")

player_name = st.text_input(
    "Enter player name (partial allowed)"
)

if player_name:

    player_data = requests.get(
        f"{BASE_URL}/player_search/{player_name}"
    ).json()

    st.write("### Player Matches")

    st.table(player_data)

# =========================
# LIVE MATCH SCORE
# =========================

st.subheader("📡 Live Match Score")

feed_placeholder = st.empty()

while True:

    try:

        data = requests.get(

            f"{BASE_URL}/live_feed/"
            f"{selected_match}/"
            f"{innings}"

        ).json()

        if data:

            lines = [

                d["text"]
                for d in data

            ]

            feed_placeholder.text(

                "\n".join(lines[-20:])

            )

        else:

            feed_placeholder.text(
                "Waiting for simulation..."
            )

    except:

        feed_placeholder.text(
            "Live feed loading..."
        )

    time.sleep(1)