from cassandra.cluster import Cluster

cluster = Cluster(['cassandra-db'])
session = cluster.connect('cricket_worldcup')

print("Building innings index...")

query = """
SELECT match_id, innings
FROM ball_by_ball
"""

rows = session.execute(query)

seen = set()

insert_query = """
INSERT INTO innings_by_match (
    match_id,
    innings
)
VALUES (%s,%s)
"""

count = 0

for row in rows:

    key = (row.match_id, row.innings)

    if key not in seen:

        seen.add(key)

        session.execute(insert_query, (

            row.match_id,
            row.innings

        ))

        count += 1

        if count % 50 == 0:
            print("Inserted:", count)

print("Innings index created.")