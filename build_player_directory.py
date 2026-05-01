from cassandra.cluster import Cluster

cluster = Cluster(['cassandra-db'])
session = cluster.connect('cricket_worldcup')

print("Building player directory...")

query = """
SELECT striker
FROM ball_by_ball
"""

rows = session.execute(query)

players = set()

for row in rows:

    players.add(row.striker)

insert_query = """
INSERT INTO players (player_name)
VALUES (%s)
"""

count = 0

for player in players:

    session.execute(insert_query, [player])

    count += 1

    if count % 50 == 0:
        print("Inserted:", count)

print("Player directory created.")