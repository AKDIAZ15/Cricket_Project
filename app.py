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

# -------------------------
# HOME ROUTE
# -------------------------

@app.route("/")
def home():

    return "Cricket Stats API Running - CI/CD DEMO V"

# -------------------------
# START SERVER
# -------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )