from cassandra.cluster import Cluster

cluster = Cluster(['cassandra-db'])
session = cluster.connect('cricket_worldcup')

print("Building player runs index...")

query = """
SELECT striker,
       match_id,
       runs_off_bat
FROM ball_by_ball
"""

rows = session.execute(query)

player_runs = {}

for row in rows:

    key = (row.striker, row.match_id)

    if key not in player_runs:
        player_runs[key] = 0

    player_runs[key] += row.runs_off_bat

insert_query = """
INSERT INTO player_runs_by_match (
    striker,
    match_id,
    runs
)
VALUES (%s,%s,%s)
"""

count = 0

for key, runs in player_runs.items():

    striker, match_id = key

    session.execute(insert_query, (

        striker,
        match_id,
        runs

    ))

    count += 1

    if count % 100 == 0:
        print("Inserted:", count)

print("Player runs index created.")