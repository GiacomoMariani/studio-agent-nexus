import sqlite3

con = sqlite3.connect("app.db")

rows = con.execute(
    """
    SELECT
        d.filename,
        c.chunk_id,
        c.page_number,
        c.text
    FROM chunks c
    JOIN documents d ON d.document_id = c.document_id
    WHERE
        lower(c.text) LIKE '%refund%'
        OR lower(c.text) LIKE '%return%'
        OR lower(c.text) LIKE '%damaged%'
    ORDER BY d.filename, c.chunk_id
    """
).fetchall()

for filename, chunk_id, page_number, text in rows:
    print("\n" + "=" * 100)
    print(f"FILE: {filename}")
    print(f"CHUNK: {chunk_id}")
    print(f"PAGE: {page_number}")
    print("-" * 100)
    print(text[:2500])
