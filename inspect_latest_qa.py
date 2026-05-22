import sqlite3

con = sqlite3.connect("app.db")

print("LATEST DOCUMENT QUERY LOGS")
print("=" * 100)

for row in con.execute(
    """
    SELECT
        question,
        answer,
        citation_count,
        was_fallback,
        latency_ms,
        created_at
    FROM document_query_logs
    ORDER BY created_at DESC
    LIMIT 5
    """
):
    question, answer, citation_count, was_fallback, latency_ms, created_at = row
    print("\nQUESTION:", question)
    print("ANSWER:", answer)
    print("CITATIONS:", citation_count)
    print("WAS_FALLBACK:", was_fallback)
    print("LATENCY_MS:", latency_ms)
    print("CREATED_AT:", created_at)

print("\n\nLATEST USAGE RECORDS")
print("=" * 100)

for row in con.execute(
    """
    SELECT
        operation,
        provider,
        model_name,
        input_tokens,
        output_tokens,
        estimated_cost_usd,
        created_at
    FROM usage_records
    ORDER BY created_at DESC
    LIMIT 10
    """
):
    print(row)
