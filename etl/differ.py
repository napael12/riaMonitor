"""
differ.py — Compute field-level changes between two monthly snapshot periods
and persist them to the ``changes`` table.
"""

from typing import Any

import psycopg2
import psycopg2.extras

# Fields we track for changes between periods
TRACKED_FIELDS = ["aum", "employees", "num_clients", "registration_status"]


def compute_changes(
    period_from: str,
    period_to: str,
    conn: "psycopg2.connection",
) -> int:
    """
    Compare snapshots for *period_from* and *period_to*, write any differences
    to the ``changes`` table, and return the number of change rows inserted.

    Detects:
    - Field-level changes (aum, employees, num_clients, registration_status)
    - New advisers (present in period_to but not period_from)
    - Terminated advisers (present in period_from but not period_to)

    The insert is idempotent via ``ON CONFLICT DO NOTHING``.
    """
    cur = conn.cursor()

    changes: list[tuple[Any, ...]] = []

    # ------------------------------------------------------------------ #
    # 1. Fetch both snapshots
    # ------------------------------------------------------------------ #
    cur.execute(
        """
        SELECT adviser_crd, aum, employees, num_clients, registration_status
        FROM snapshots
        WHERE period = %s
        """,
        (period_from,),
    )
    snap_from: dict[str, dict] = {
        row[0]: {
            "aum": row[1],
            "employees": row[2],
            "num_clients": row[3],
            "registration_status": row[4],
        }
        for row in cur.fetchall()
    }

    cur.execute(
        """
        SELECT adviser_crd, aum, employees, num_clients, registration_status
        FROM snapshots
        WHERE period = %s
        """,
        (period_to,),
    )
    snap_to: dict[str, dict] = {
        row[0]: {
            "aum": row[1],
            "employees": row[2],
            "num_clients": row[3],
            "registration_status": row[4],
        }
        for row in cur.fetchall()
    }

    crds_from = set(snap_from.keys())
    crds_to = set(snap_to.keys())

    # ------------------------------------------------------------------ #
    # 2. New advisers
    # ------------------------------------------------------------------ #
    for crd in crds_to - crds_from:
        changes.append(
            (crd, period_from, period_to, "adviser_status", None, "new")
        )

    # ------------------------------------------------------------------ #
    # 3. Terminated advisers
    # ------------------------------------------------------------------ #
    for crd in crds_from - crds_to:
        changes.append(
            (crd, period_from, period_to, "adviser_status", "active", "terminated")
        )

    # ------------------------------------------------------------------ #
    # 4. Field-level changes for advisers present in both periods
    # ------------------------------------------------------------------ #
    for crd in crds_from & crds_to:
        old = snap_from[crd]
        new = snap_to[crd]
        for field in TRACKED_FIELDS:
            old_val = _normalise(old.get(field))
            new_val = _normalise(new.get(field))
            if old_val != new_val:
                changes.append(
                    (
                        crd,
                        period_from,
                        period_to,
                        field,
                        old_val,
                        new_val,
                    )
                )

    # ------------------------------------------------------------------ #
    # 5. Insert (idempotent)
    # ------------------------------------------------------------------ #
    if changes:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO changes
                (adviser_crd, period_from, period_to, field, old_value, new_value)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            changes,
            page_size=500,
        )
        conn.commit()

    cur.close()
    print(
        f"[differ] {len(changes):,} changes detected "
        f"({period_from} → {period_to})"
    )
    return len(changes)


def get_previous_period(period: str, conn: "psycopg2.connection") -> str | None:
    """
    Return the most recent period in the snapshots table that is strictly
    earlier than *period*, or None if there is no prior period.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT period FROM snapshots
        WHERE period < %s
        GROUP BY period
        ORDER BY period DESC
        LIMIT 1
        """,
        (period,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(value: Any) -> str | None:
    """Convert a DB value to a comparable string, treating None/NULL uniformly."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None
