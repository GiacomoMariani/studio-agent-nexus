import sqlite3

from services.document_qa_prompt_builder import _remove_demo_notice_text

con = sqlite3.connect("app.db")

row = con.execute(
    """
    SELECT c.text
    FROM chunks c
    JOIN documents d ON d.document_id = c.document_id
    WHERE d.filename = 'demo_customer_support_faq.pdf'
      AND lower(c.text) LIKE '%does not describe any real company policy%'
    LIMIT 1
    """
).fetchone()

if row is None:
    print("No matching chunk found.")
    raise SystemExit

raw_text = row[0]
clean_text = _remove_demo_notice_text(raw_text)

print("RAW:")
print(raw_text[:1000])

print("\n" + "=" * 100 + "\n")

print("CLEANED:")
print(clean_text[:1000])
