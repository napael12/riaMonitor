"""
loader.py — Upsert parsed adviser snapshots into PostgreSQL.
Uses psycopg2 directly (not SQLAlchemy ORM) for efficient batch upserts.
"""

from typing import Any

import pandas as pd
import psycopg2
import psycopg2.extras


def load_snapshot(
    df: pd.DataFrame,
    period: str,
    conn: "psycopg2.connection",
) -> int:
    """
    Upsert all rows in *df* into the ``advisers`` and ``snapshots`` tables.

    Parameters
    ----------
    df : pd.DataFrame
        Output of ``parser.parse_xlsx`` — must contain the canonical columns.
    period : str
        Period string in ``YYYY-MM`` format.
    conn : psycopg2 connection
        Open database connection (not autocommit; caller manages transactions).

    Returns
    -------
    int
        Number of snapshot rows inserted or updated.
    """
    cur = conn.cursor()

    # ------------------------------------------------------------------ #
    # 1. Upsert advisers
    # ------------------------------------------------------------------ #
    adviser_rows: list[tuple[Any, ...]] = []
    for _, row in df.iterrows():
        adviser_rows.append(
            (
                _val(row, "crd"),
                _val(row, "firm_name") or "Unknown",
                _val(row, "registration_type"),
                _val(row, "sec_number"),
                _val(row, "primary_state"),
            )
        )

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO advisers (crd, firm_name, registration_type, sec_number, primary_state, updated_at)
        VALUES %s
        ON CONFLICT (crd) DO UPDATE SET
            firm_name         = EXCLUDED.firm_name,
            registration_type = EXCLUDED.registration_type,
            sec_number        = EXCLUDED.sec_number,
            primary_state     = EXCLUDED.primary_state,
            updated_at        = NOW()
        """,
        adviser_rows,
        template="(%s, %s, %s, %s, %s, NOW())",
        page_size=500,
    )

    # ------------------------------------------------------------------ #
    # 2. Upsert snapshots
    # ------------------------------------------------------------------ #
    snapshot_rows: list[tuple[Any, ...]] = []
    for _, row in df.iterrows():
        aum = _numeric(row, "aum")
        employees = _int(row, "employees")
        num_clients = _int(row, "num_clients")

        snapshot_rows.append(
            (
                _val(row, "crd"),
                period,
                aum,
                employees,
                num_clients,
                _val(row, "registration_status"),
                _val(row, "raw"),
            )
        )

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO snapshots (adviser_crd, period, aum, employees, num_clients, registration_status, raw)
        VALUES %s
        ON CONFLICT (adviser_crd, period) DO UPDATE SET
            aum                 = EXCLUDED.aum,
            employees           = EXCLUDED.employees,
            num_clients         = EXCLUDED.num_clients,
            registration_status = EXCLUDED.registration_status,
            raw                 = EXCLUDED.raw,
            ingested_at         = NOW()
        """,
        snapshot_rows,
        page_size=500,
    )

    conn.commit()
    cur.close()

    count = len(snapshot_rows)
    print(f"[loader] Upserted {count:,} snapshots for period {period}")
    return count


def period_already_ingested(period: str, conn: "psycopg2.connection") -> bool:
    """
    Return True if the ``snapshots`` table already contains rows for *period*.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM snapshots WHERE period = %s LIMIT 1",
        (period,),
    )
    row = cur.fetchone()
    cur.close()
    return row is not None and row[0] > 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _val(row: pd.Series, col: str) -> Any:
    """Return None for NaN/None/empty, otherwise return the raw value."""
    v = row.get(col)
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    s = str(v).strip()
    if s in ("", "nan", "None"):
        return None
    return s


def _numeric(row: pd.Series, col: str):
    """Return a Python float or None."""
    v = row.get(col)
    if v is None:
        return None
    try:
        f = float(v)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _int(row: pd.Series, col: str):
    """Return a Python int or None."""
    v = _numeric(row, col)
    if v is None:
        return None
    return int(v)
