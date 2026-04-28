from flask import Flask, jsonify
import redis
import ast
from cassandra.cluster import Cluster

app = Flask(__name__)

# -------------------------
# Redis Connection
# -------------------------

r = redis.Redis(
    host='127.0.0.1',
    port=6379,
    decode_responses=True
)

# -------------------------
# Cassandra Connection
# -------------------------

cluster = Cluster(['127.0.0.1'])
session = cluster.connect('cricket_worldcup')

# -------------------------
# HOME
# -------------------------

@app.route("/")
def home():
    return "Cricket Stats API Running - Updated Version"

# -------------------------
# GET YEARS
# -------------------------

@app.route("/years")
def get_years():

    query = """
    SELECT DISTINCT season
    FROM matches_by_year
    """

    rows = session.execute(query)

    years = []

    for row in rows:
        years.append(row.season)

    years.sort()

    return jsonify(years)

# -------------------------
# GET MATCHES BY YEAR
# -------------------------

@app.route("/matches/<int:year>")
def get_matches(year):

    query = """
    SELECT match_id,
           batting_team,
           bowling_team,
           venue
    FROM matches_by_year
    WHERE season=%s
    """

    rows = session.execute(query, [year])

    matches = []

    for row in rows:

        label = (
            str(row.match_id)
            + " — "
            + row.batting_team
            + " vs "
            + row.bowling_team
            + " — "
            + row.venue
        )

        matches.append({
            "match_id": row.match_id,
            "label": label
        })

    return jsonify(matches)

# -------------------------
# GET INNINGS
# -------------------------

@app.route("/innings/<int:match_id>")
def get_innings(match_id):

    query = """
    SELECT innings
    FROM innings_by_match
    WHERE match_id=%s
    """

    rows = session.execute(query, [match_id])

    innings_list = []

    for row in rows:
        innings_list.append(row.innings)

    innings_list.sort()

    return jsonify(innings_list)
# -------------------------
# GET BALLS
# -------------------------

@app.route("/balls/<int:match_id>/<int:innings>")
def get_balls(match_id, innings):

    query = """
    SELECT over,
           ball,
           striker,
           bowler,
           runs_off_bat,
           wides,
           noballs,
           wicket_type
    FROM ball_by_ball
    WHERE match_id=%s
      AND innings=%s
    """

    rows = session.execute(query, [match_id, innings])

    balls = []

    for row in rows:

        balls.append({

            "over": row.over,
            "ball": row.ball,
            "striker": row.striker,
            "bowler": row.bowler,
            "runs": row.runs_off_bat,
            "wides": row.wides,
            "noballs": row.noballs,
            "wicket": row.wicket_type

        })

    return jsonify(balls)

# -------------------------
# LIVE SCORE (Redis)
# -------------------------

@app.route("/live/<int:match_id>")
def live_score(match_id):

    key = f"match:{match_id}"

    data = r.hgetall(key)

    return jsonify(data)

# -------------------------
@app.route("/match_summary/<int:match_id>")
def match_summary(match_id):

    total_runs = 0
    wickets = 0

    wides = 0
    noballs = 0
    byes = 0
    legbyes = 0

    teams = set()
    venue = ""

    # Get innings list first
    innings_query = """
    SELECT innings
    FROM innings_by_match
    WHERE match_id=%s
    """

    innings_rows = session.execute(
        innings_query,
        [match_id]
    )

    innings_list = []

    for row in innings_rows:
        innings_list.append(row.innings)

    # Query each innings separately
    for innings in innings_list:

        query = """
        SELECT batting_team,
               bowling_team,
               venue,
               runs_off_bat,
               wides,
               noballs,
               byes,
               legbyes,
               wicket_type
        FROM ball_by_ball
        WHERE match_id=%s
          AND innings=%s
        """

        rows = session.execute(
            query,
            [match_id, innings]
        )

        for row in rows:

            teams.add(row.batting_team)
            teams.add(row.bowling_team)

            venue = row.venue

            total_runs += row.runs_off_bat

            wides += row.wides
            noballs += row.noballs
            byes += row.byes
            legbyes += row.legbyes

            if row.wicket_type:
                wickets += 1

    team_list = list(teams)

    return jsonify({

        "teams": team_list,
        "venue": venue,

        "runs": total_runs,
        "wickets": wickets,

        "extras": {

            "wides": wides,
            "noballs": noballs,
            "byes": byes,
            "legbyes": legbyes

        }

    })

@app.route("/player_search/<search_text>")
def player_search(search_text):

    # Step 1: Get all player names

    query = """
    SELECT player_name
    FROM players
    """

    rows = session.execute(query)

    matched_players = []

    search_text = search_text.lower()

    for row in rows:

        name = row.player_name

        if search_text in name.lower():

            matched_players.append(name)

    results = []

    # Step 2: Fetch match stats for matched players

    for player in matched_players:

        query2 = """
        SELECT match_id,
               runs
        FROM player_runs_by_match
        WHERE striker=%s
        """

        rows2 = session.execute(query2, [player])

        for r in rows2:

            results.append({

                "player": player,
                "match_id": r.match_id,
                "runs": r.runs

            })

    return jsonify(results)
@app.route("/wicket_types/<int:match_id>")
def wicket_types(match_id):

    query = """
    SELECT innings
    FROM innings_by_match
    WHERE match_id=%s
    """

    innings_rows = session.execute(
        query,
        [match_id]
    )

    wicket_set = set()

    for row in innings_rows:

        innings = row.innings

        query2 = """
        SELECT wicket_type
        FROM ball_by_ball
        WHERE match_id=%s
          AND innings=%s
        """

        rows = session.execute(
            query2,
            [match_id, innings]
        )

        for r in rows:

            if r.wicket_type:
                wicket_set.add(r.wicket_type)

    return jsonify(list(wicket_set))
@app.route("/extras/<int:match_id>")
def extras(match_id):

    wides = 0
    noballs = 0
    byes = 0
    legbyes = 0

    query = """
    SELECT innings
    FROM innings_by_match
    WHERE match_id=%s
    """

    innings_rows = session.execute(
        query,
        [match_id]
    )

    for row in innings_rows:

        innings = row.innings

        query2 = """
        SELECT wides,
               noballs,
               byes,
               legbyes
        FROM ball_by_ball
        WHERE match_id=%s
          AND innings=%s
        """

        rows = session.execute(
            query2,
            [match_id, innings]
        )

        for r in rows:

            wides += r.wides
            noballs += r.noballs
            byes += r.byes
            legbyes += r.legbyes

    return jsonify({

        "wides": wides,
        "noballs": noballs,
        "byes": byes,
        "legbyes": legbyes

    })

@app.route(
    "/live_feed/<int:match_id>/<int:innings>"
)
def live_feed(match_id, innings):

    key = f"live_feed:{match_id}:{innings}"

    raw_lines = r.lrange(key, 0, -1)

    lines = []

    for item in raw_lines:

        lines.append(
            ast.literal_eval(item)
        )

    return jsonify(lines)
@app.route(
    "/wicket_players/<int:match_id>/<wicket_type>"
)
def wicket_players(match_id, wicket_type):

    query = """
    SELECT player_dismissed, wicket_type
    FROM ball_by_ball
    WHERE match_id=%s
    ALLOW FILTERING
    """

    rows = session.execute(
        query,
        [match_id]
    )

    players = []

    for row in rows:

        if row.wicket_type:

            if row.wicket_type.lower() == wicket_type.lower():

                players.append({

                    "player": row.player_dismissed,
                    "wicket": row.wicket_type

                })

    return jsonify(players)

if __name__ == "__main__":
    app.run(debug=True)