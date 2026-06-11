"""Lightweight schema reconciliation for the SQLAlchemy stores.

`Base.metadata.create_all()` only creates *missing* tables — it never alters an existing
one. So when a model gains, drops, or renames a column, a table created by an earlier
version keeps its old shape and every query referencing the new column fails at runtime
(`sqlite3.OperationalError: no such column`). That is exactly how a persisted `app.db`
silently broke the Board's `GET /reviews` after the reviews schema moved from
`review_id`/`created_at` to `task_id`/`updated_at`.

A full migration tool (Alembic) is still deferred. This bridges the gap conservatively:
when the persisted columns drift from the model, rebuild the table if it is **empty**
(lossless), otherwise raise so a human migrates real data deliberately — we never drop
rows on our own.
"""

from sqlalchemy import Engine, func, inspect, select


def reconcile_table(engine: Engine, model: type) -> None:
    """Rebuild `model`'s table if its on-disk columns drift from the model's, but only
    when the table is empty; raise on drift over a non-empty table."""
    table = model.__table__
    inspector = inspect(engine)

    if not inspector.has_table(table.name):
        return  # absent — create_all() will build it correctly

    on_disk = {column["name"] for column in inspector.get_columns(table.name)}
    declared = {column.name for column in table.columns}
    if on_disk == declared:
        return  # in sync — nothing to do

    with engine.connect() as conn:
        row_count = conn.execute(select(func.count()).select_from(table)).scalar_one()

    if row_count:
        raise RuntimeError(
            f"Schema drift in table '{table.name}': on-disk columns {sorted(on_disk)} "
            f"do not match model columns {sorted(declared)}, and the table holds "
            f"{row_count} row(s). Migrate the data manually — refusing to drop rows."
        )

    table.drop(engine)
    table.create(engine)
