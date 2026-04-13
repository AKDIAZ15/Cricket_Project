import pandas as pd
from cassandra.cluster import Cluster
from cassandra.query import BatchStatement

# -------------------------
# Cassandra Connection
# -------------------------

cluster = Cluster(['127.0.0.1'])
session = cluster.connect('cricket_worldcup')

# -------------------------
# Load CSV
# -------------------------

df = pd.read_csv("deliveries.csv")

print("CSV Loaded")

# -------------------------
# Insert Query
# -------------------------

insert_query = """
INSERT INTO ball_by_ball (

    match_id,
    season,
    start_date,
    venue,

    innings,
    over,
    ball,

    batting_team,
    bowling_team,

    striker,
    non_striker,
    bowler,

    runs_off_bat,
    extras,

    wides,
    noballs,
    byes,
    legbyes,
    penalty,

    wicket_type,
    player_dismissed,
    other_wicket_type,
    other_player_dismissed

)

VALUES (

    %s,%s,%s,%s,
    %s,%s,%s,
    %s,%s,
    %s,%s,%s,
    %s,%s,
    %s,%s,%s,%s,%s,
    %s,%s,%s,%s

)
"""

# -------------------------
# Batch Insert
# -------------------------

batch_size = 20

batch = BatchStatement()

count = 0

for _, row in df.iterrows():

    ball_value = str(row["ball"])

    if "." in ball_value:
        over, ball = ball_value.split(".")
    else:
        over = 0
        ball = ball_value

    batch.add(insert_query, (

        int(row["match_id"]),
        int(row["season"]),
        str(row["start_date"]),
        str(row["venue"]),

        int(row["innings"]),
        int(over),
        int(ball),

        str(row["batting_team"]),
        str(row["bowling_team"]),

        str(row["striker"]),
        str(row["non_striker"]),
        str(row["bowler"]),

        int(row["runs_off_bat"]),
        int(row["extras"]),

        int(row["wides"]) if pd.notna(row["wides"]) else 0,
        int(row["noballs"]) if pd.notna(row["noballs"]) else 0,
        int(row["byes"]) if pd.notna(row["byes"]) else 0,
        int(row["legbyes"]) if pd.notna(row["legbyes"]) else 0,
        int(row["penalty"]) if pd.notna(row["penalty"]) else 0,

        str(row["wicket_type"]) if pd.notna(row["wicket_type"]) else None,
        str(row["player_dismissed"]) if pd.notna(row["player_dismissed"]) else None,
        str(row["other_wicket_type"]) if pd.notna(row["other_wicket_type"]) else None,
        str(row["other_player_dismissed"]) if pd.notna(row["other_player_dismissed"]) else None

    ))

    count += 1

    # Execute batch every 500 rows
    if count % batch_size == 0:

        session.execute(batch)

        batch = BatchStatement()

        print("Inserted:", count)

# Insert remaining rows
if batch:

    session.execute(batch)

print("Data Insert Complete")