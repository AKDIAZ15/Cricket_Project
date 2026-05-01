from cassandra.cluster import Cluster

cluster = Cluster(['cassandra-db'])
session = cluster.connect('cricket_worldcup')

print("Building match index...")

query = """
SELECT match_id,
       season,
       batting_team,
       bowling_team,
       venue
FROM ball_by_ball
"""

rows = session.execute(query)

seen = set()

insert_query = """
INSERT INTO matches_by_year (
    season,
    match_id,
    batting_team,
    bowling_team,
    venue
)
VALUES (%s,%s,%s,%s,%s)
"""

count = 0

for row in rows:

    key = (row.season, row.match_id)

    if key not in seen:

        seen.add(key)

        session.execute(insert_query, (

            row.season,
            row.match_id,
            row.batting_team,
            row.bowling_team,
            row.venue

        ))

        count += 1

        if count % 50 == 0:
            print("Inserted matches:", count)

print("Match index created successfully.")