import ast
import csv
import os

from flask import Flask, jsonify
import redis

try:
    from cassandra.cluster import Cluster
except ModuleNotFoundError:
    Cluster = None

app = Flask(__name__)

# -------------------------
# Redis Connection
# -------------------------

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=6379,
    decode_responses=True
)

# -------------------------
# Cassandra Connection
# -------------------------

session = None
csv_rows = []


def to_int(value):
    if value in (None, ""):
        return 0

    return int(float(value))


def load_csv_rows():
    rows = []

    with open("deliveries.csv", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            ball_value = str(row["ball"])

            if "." in ball_value:
                over, ball = ball_value.split(".", 1)
            else:
                over = "0"
                ball = ball_value

            row["match_id"] = to_int(row["match_id"])
            row["season"] = to_int(row["season"])
            row["innings"] = to_int(row["innings"])
            row["over"] = to_int(over)
            row["ball_no"] = to_int(ball)
            row["runs_off_bat"] = to_int(row["runs_off_bat"])
            row["wides"] = to_int(row["wides"])
            row["noballs"] = to_int(row["noballs"])
            row["byes"] = to_int(row["byes"])
            row["legbyes"] = to_int(row["legbyes"])

            rows.append(row)

    print("Cassandra unavailable. Using deliveries.csv fallback.")
    print(f"Loaded {len(rows)} ball records from CSV.")

    return rows


try:
    if Cluster is None:
        raise RuntimeError("cassandra-driver is not installed")

    cluster = Cluster([os.getenv("CASSANDRA_HOST", "127.0.0.1")])
    session = cluster.connect("cricket_worldcup")
    print("Connected to Cassandra.")
except Exception as exc:
    print(f"Could not connect to Cassandra: {exc}")
    csv_rows = load_csv_rows()


def rows_for_match(match_id):
    return [
        row for row in csv_rows
        if row["match_id"] == match_id
    ]


def rows_for_innings(match_id, innings):
    rows = [
        row for row in csv_rows
        if row["match_id"] == match_id
        and row["innings"] == innings
    ]

    return sorted(
        rows,
        key=lambda row: (row["over"], row["ball_no"])
    )


# -------------------------
# HOME
# -------------------------

@app.route("/")
def home():
    return "Cricket Stats API Running - CI/CD DEMO V" 


# -------------------------
# GET YEARS
# -------------------------

@app.route("/years")
def get_years():
    if session is None:
        years = sorted({row["season"] for row in csv_rows})
        return jsonify(years)

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
    if session is None:
        seen = {}

        for row in csv_rows:
            if row["season"] != year:
                continue

            match_id = row["match_id"]

            if match_id not in seen:
                label = (
                    str(match_id)
                    + " - "
                    + row["batting_team"]
                    + " vs "
                    + row["bowling_team"]
                    + " - "
                    + row["venue"]
                )

                seen[match_id] = {
                    "match_id": match_id,
                    "label": label
                }

        return jsonify(list(seen.values()))

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
            + " - "
            + row.batting_team
            + " vs "
            + row.bowling_team
            + " - "
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
    if session is None:
        innings_list = sorted({
            row["innings"] for row in rows_for_match(match_id)
        })

        return jsonify(innings_list)

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
    if session is None:
        balls = []

        for row in rows_for_innings(match_id, innings):
            balls.append({
                "over": row["over"],
                "ball": row["ball_no"],
                "striker": row["striker"],
                "bowler": row["bowler"],
                "runs": row["runs_off_bat"],
                "wides": row["wides"],
                "noballs": row["noballs"],
                "wicket": row["wicket_type"] or None
            })

        return jsonify(balls)

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

    if session is None:
        for row in rows_for_match(match_id):
            teams.add(row["batting_team"])
            teams.add(row["bowling_team"])

            venue = row["venue"]
            total_runs += row["runs_off_bat"]
            wides += row["wides"]
            noballs += row["noballs"]
            byes += row["byes"]
            legbyes += row["legbyes"]

            if row["wicket_type"]:
                wickets += 1

        return jsonify({
            "teams": list(teams),
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

    return jsonify({
        "teams": list(teams),
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
    if session is None:
        search_text = search_text.lower()
        player_runs = {}

        for row in csv_rows:
            player = row["striker"]

            if search_text not in player.lower():
                continue

            key = (player, row["match_id"])
            player_runs[key] = player_runs.get(key, 0) + row["runs_off_bat"]

        results = []

        for (player, match_id), runs in player_runs.items():
            results.append({
                "player": player,
                "match_id": match_id,
                "runs": runs
            })

        return jsonify(results)

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

    for player in matched_players:
        query2 = """
        SELECT match_id,
               runs
        FROM player_runs_by_match
        WHERE striker=%s
        """

        rows2 = session.execute(query2, [player])

        for r_row in rows2:
            results.append({
                "player": player,
                "match_id": r_row.match_id,
                "runs": r_row.runs
            })

    return jsonify(results)


@app.route("/wicket_types/<int:match_id>")
def wicket_types(match_id):
    if session is None:
        wicket_set = {
            row["wicket_type"]
            for row in rows_for_match(match_id)
            if row["wicket_type"]
        }

        return jsonify(list(wicket_set))

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

        for result_row in rows:
            if result_row.wicket_type:
                wicket_set.add(result_row.wicket_type)

    return jsonify(list(wicket_set))


@app.route("/extras/<int:match_id>")
def extras(match_id):
    wides = 0
    noballs = 0
    byes = 0
    legbyes = 0

    if session is None:
        for row in rows_for_match(match_id):
            wides += row["wides"]
            noballs += row["noballs"]
            byes += row["byes"]
            legbyes += row["legbyes"]

        return jsonify({
            "wides": wides,
            "noballs": noballs,
            "byes": byes,
            "legbyes": legbyes
        })

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

        for result_row in rows:
            wides += result_row.wides
            noballs += result_row.noballs
            byes += result_row.byes
            legbyes += result_row.legbyes

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
    if session is None:
        players = []

        for row in rows_for_match(match_id):
            row_wicket = row["wicket_type"]

            if row_wicket and row_wicket.lower() == wicket_type.lower():
                players.append({
                    "player": row["player_dismissed"],
                    "wicket": row_wicket
                })

        return jsonify(players)

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
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
