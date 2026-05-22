import sqlite3

con = sqlite3.connect("app.db")

tables = [
    row[0]
    for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
]

print("TABLES:")
for table in tables:
    print(table)

print("\nCOLUMNS:")
for table in tables:
    columns = [
        col[1]
        for col in con.execute(f"PRAGMA table_info({table})")
    ]
    print(f"\n{table}: {', '.join(columns)}")
