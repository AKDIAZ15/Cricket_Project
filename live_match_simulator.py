from cassandra.cluster import Cluster
import redis
import time

# -------------------------
# Cassandra Connection
# -------------------------

cluster = Cluster(['cassandra-db'])
session = cluster.connect('cricket_worldcup')

# -------------------------
# Redis Connection
# -------------------------

r = redis.Redis(
    host='127.0.0.1',
    port=6379,
    decode_responses=True
)

# -------------------------
# Select Match
# -------------------------

match_id = 335982

# Clear old live data
r.delete(f"live_match:{match_id}")

# -------------------------
# Fetch Ball Data
# -------------------------

query = """
SELECT match_id,
       runs_off_bat,
       extras,
       wicket_type
FROM ball_by_ball
WHERE match_id=%s
ALLOW FILTERING
"""

rows = session.execute(query, [match_id])

print("🏏 Starting Live Match Simulation...")

total_runs = 0
wickets = 0
ball_count = 0

# -------------------------
# Simulate Ball-by-Ball
# -------------------------

for row in rows:

    runs = row.runs_off_bat + row.extras

    total_runs += runs
    ball_count += 1

    if row.wicket_type:
        wickets += 1

    # Calculate Live Run Rate

    overs = ball_count / 6

    runrate = (
        total_runs / overs
        if overs > 0 else 0
    )

    key = f"live_match:{match_id}"

    # Store Live Stats

    r.hset(key, "runs", total_runs)
    r.hset(key, "wickets", wickets)
    r.hset(key, "balls", ball_count)
    r.hset(key, "runrate", round(runrate, 2))

    print(
        "Ball:", ball_count,
        "| Runs:", total_runs,
        "| Wickets:", wickets,
        "| Runrate:", round(runrate, 2)
    )

    # Delay = Live Simulation
    time.sleep(1)

print("✅ Match Simulation Complete")