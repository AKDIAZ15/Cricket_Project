import time
import requests
import redis

BASE_URL = "http://127.0.0.1:5000"

r = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True
)

match_id = int(input("Enter Match ID: "))
innings = int(input("Enter Innings: "))

print("Fetching balls...")

response = requests.get(
    f"{BASE_URL}/balls/{match_id}/{innings}"
)

balls = response.json()

runs = 0
wickets = 0
balls_count = 0

# Clear old feed
r.delete(
    f"live_feed:{match_id}:{innings}"
)

print("Starting live simulation...\n")

for ball in balls:

    over = ball["over"]
    ball_no = ball["ball"]

    striker = ball["striker"]
    bowler = ball["bowler"]

    ball_runs = ball["runs"]

    wicket = ball["wicket"] or "None"

    # Update totals
    runs += ball_runs

    if wicket != "None":
        wickets += 1

    balls_count += 1

    # Update Redis score
    key = f"match:{match_id}"

    r.hset(
        key,
        mapping={
            "runs": runs,
            "wickets": wickets,
            "balls": balls_count
        }
    )

    # CMD line
    line = (

        f"Over {over}.{ball_no} | "
        f"{striker} vs {bowler} | "
        f"Runs: {runs}/{wickets}"

    )

    print(line)

    # Store structured data
    r.rpush(

        f"live_feed:{match_id}:{innings}",

        str({

            "text": line,
            "wicket": wicket.lower()

        })

    )

    time.sleep(1)

print("\nSimulation Finished")