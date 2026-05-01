import ast
import csv
import os
import time

from flask import Flask, jsonify
import redis

try:
    from cassandra.cluster import Cluster
except ModuleNotFoundError:
    Cluster = None

app = Flask(__name__)

# -------------------------
# Redis Connection (FIXED)
# -------------------------

print("⏳ Connecting to Redis...")

redis_host = os.getenv("REDIS_HOST", "redis-cache")

for i in range(30):

    try:

        r = redis.Redis(
            host=redis_host,
            port=6379,
            decode_responses=True
        )

        r.ping()

        print("✅ Connected to Redis")

        break

    except Exception:

        print("⏳ Redis not ready yet... retrying")
        time.sleep(2)

else:

    raise Exception(
        "❌ Could not connect to Redis after retries"
    )

# -------------------------
# Cassandra Connection
# -------------------------

session = None
csv_rows = []


def rows_for_match(match_id):
    return [
        row for row in csv_rows
        if row["match_id"] == match_id
    ]


def wicket_count(rows):
    return sum(
        1 for row in rows
        if row.get("player_dismissed")
    )

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

    print("Cassandra unavailable. Using CSV fallback.")

    return rows


try:

    if Cluster is None:
        raise RuntimeError("cassandra-driver not installed")

    cass_host = os.getenv(
        "CASSANDRA_HOST",
        "cassandra-db"
    )

    print("⏳ Connecting to Cassandra...")

    cluster = Cluster([cass_host])
    session = cluster.connect("cricket_worldcup")

    print("✅ Connected to Cassandra.")

except Exception as exc:

    print(f"Could not connect to Cassandra: {exc}")

    csv_rows = load_csv_rows()

# -------------------------
# SAFE LIVE FEED (FIXED)
# -------------------------

@app.route(
    "/live_feed/<int:match_id>/<int:innings>"
)
def live_feed(match_id, innings):

    key = f"live_feed:{match_id}:{innings}"

    try:

        raw_lines = r.lrange(key, 0, -1)

    except Exception:

        return jsonify([])

    lines = []

    for item in raw_lines:

        try:

            lines.append(
                ast.literal_eval(item)
            )

        except Exception:

            continue

    return jsonify(lines)


@app.route("/years")
def years():

    seasons = sorted(
        {
            row["season"]
            for row in csv_rows
        }
    )

    return jsonify(seasons)


@app.route("/matches/<int:season>")
def matches(season):

    seen = {}

    for row in csv_rows:

        if row["season"] != season:
            continue

        match_id = row["match_id"]

        if match_id not in seen:
            seen[match_id] = {
                "match_id": match_id,
                "teams": [],
                "venue": row["venue"]
            }

        for team_key in ("batting_team", "bowling_team"):
            team = row[team_key]

            if team and team not in seen[match_id]["teams"]:
                seen[match_id]["teams"].append(team)

    match_list = []

    for match in seen.values():

        teams = " vs ".join(match["teams"][:2])

        match_list.append(
            {
                "match_id": match["match_id"],
                "label": f'{match["match_id"]} - {teams} at {match["venue"]}'
            }
        )

    return jsonify(
        sorted(match_list, key=lambda item: item["match_id"])
    )


@app.route("/innings/<int:match_id>")
def innings(match_id):

    return jsonify(
        sorted(
            {
                row["innings"]
                for row in rows_for_match(match_id)
            }
        )
    )


@app.route("/match_summary/<int:match_id>")
def match_summary(match_id):

    rows = rows_for_match(match_id)

    teams = []

    for row in rows:
        for team_key in ("batting_team", "bowling_team"):
            team = row[team_key]

            if team and team not in teams:
                teams.append(team)

    return jsonify(
        {
            "teams": teams[:2],
            "venue": rows[0]["venue"] if rows else "Unknown",
            "runs": sum(
                row["runs_off_bat"]
                + row["wides"]
                + row["noballs"]
                + row["byes"]
                + row["legbyes"]
                for row in rows
            ),
            "wickets": wicket_count(rows)
        }
    )


@app.route("/extras/<int:match_id>")
def extras(match_id):

    rows = rows_for_match(match_id)

    return jsonify(
        {
            "wides": sum(row["wides"] for row in rows),
            "noballs": sum(row["noballs"] for row in rows),
            "byes": sum(row["byes"] for row in rows),
            "legbyes": sum(row["legbyes"] for row in rows)
        }
    )


@app.route("/wicket_types/<int:match_id>")
def wicket_types(match_id):

    types = sorted(
        {
            row["wicket_type"]
            for row in rows_for_match(match_id)
            if row.get("wicket_type")
        }
    )

    return jsonify(types)


@app.route("/wicket_players/<int:match_id>/<wicket_type>")
def wicket_players(match_id, wicket_type):

    players = []

    for row in rows_for_match(match_id):

        if row.get("wicket_type") != wicket_type:
            continue

        players.append(
            {
                "player": row.get("player_dismissed") or "Unknown",
                "wicket_type": row["wicket_type"],
                "bowler": row.get("bowler") or "Unknown",
                "innings": row["innings"],
                "over": row["over"],
                "ball": row["ball_no"]
            }
        )

    return jsonify(players)


@app.route("/player_search/<player_name>")
def player_search(player_name):

    query = player_name.lower()
    player_matches = {}

    for row in csv_rows:

        striker = row["striker"]

        if query not in striker.lower():
            continue

        key = (striker, row["match_id"])

        if key not in player_matches:
            player_matches[key] = {
                "player": striker,
                "match_id": row["match_id"],
                "season": row["season"],
                "runs": 0
            }

        player_matches[key]["runs"] += row["runs_off_bat"]

    return jsonify(
        sorted(
            player_matches.values(),
            key=lambda item: (item["player"], item["season"], item["match_id"])
        )[:100]
    )

# -------------------------
# HOME ROUTE
# -------------------------

@app.route("/")
def home():

    return "Cricket Stats API Running - CI/CD DEMO V"


@app.route("/health")
def health():

    return jsonify(
        {
            "status": "ok",
            "redis": "connected",
            "cassandra": "connected" if session else "csv_fallback"
        }
    )

# -------------------------
# START SERVER
# -------------------------

if __name__ == "__main__":

    debug_enabled = os.getenv("FLASK_DEBUG", "0") == "1"

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug_enabled,
        use_reloader=debug_enabled
    )
