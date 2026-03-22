"""
routers/advisers.py — Adviser-related API endpoints.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Adviser, Change, Snapshot

router = APIRouter(prefix="/advisers", tags=["advisers"])


# ---------------------------------------------------------------------------
# GET /advisers
# ---------------------------------------------------------------------------

@router.get("")
async def list_advisers(
    q: Optional[str] = Query(None, description="Firm name search (case-insensitive)"),
    state: Optional[str] = Query(None, description="Primary state (2-letter code)"),
    min_aum: Optional[float] = Query(None, description="Minimum AUM filter"),
    max_aum: Optional[float] = Query(None, description="Maximum AUM filter"),
    registration_type: Optional[str] = Query(None, description="'SEC' or 'Exempt'"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Search and filter advisers. Returns each adviser with their latest
    snapshot AUM and employee count.
    """
    # Sub-query: latest period per adviser
    latest_period_sq = (
        select(
            Snapshot.adviser_crd,
            func.max(Snapshot.period).label("latest_period"),
        )
        .group_by(Snapshot.adviser_crd)
        .subquery("latest_period_sq")
    )

    # Join advisers → latest snapshot
    stmt = (
        select(
            Adviser.crd,
            Adviser.firm_name,
            Adviser.registration_type,
            Adviser.sec_number,
            Adviser.primary_state,
            Snapshot.aum,
            Snapshot.employees,
            Snapshot.num_clients,
            Snapshot.registration_status,
            Snapshot.period,
        )
        .outerjoin(
            latest_period_sq,
            Adviser.crd == latest_period_sq.c.adviser_crd,
        )
        .outerjoin(
            Snapshot,
            (Snapshot.adviser_crd == latest_period_sq.c.adviser_crd)
            & (Snapshot.period == latest_period_sq.c.latest_period),
        )
    )

    # Filters
    if q:
        stmt = stmt.where(Adviser.firm_name.ilike(f"%{q}%"))
    if state:
        stmt = stmt.where(Adviser.primary_state == state.upper())
    if registration_type:
        stmt = stmt.where(Adviser.registration_type == registration_type)
    if min_aum is not None:
        stmt = stmt.where(Snapshot.aum >= min_aum)
    if max_aum is not None:
        stmt = stmt.where(Snapshot.aum <= max_aum)

    # Count total (before pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginate
    stmt = stmt.order_by(Adviser.firm_name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.fetchall()

    items = [
        {
            "crd": row.crd,
            "firm_name": row.firm_name,
            "registration_type": row.registration_type,
            "sec_number": row.sec_number,
            "primary_state": row.primary_state,
            "aum": float(row.aum) if row.aum is not None else None,
            "employees": row.employees,
            "num_clients": row.num_clients,
            "registration_status": row.registration_status,
            "latest_period": row.period,
        }
        for row in rows
    ]

    return {"total": total, "items": items, "offset": offset, "limit": limit}


# ---------------------------------------------------------------------------
# GET /advisers/{crd}
# ---------------------------------------------------------------------------

@router.get("/{crd}")
async def get_adviser(
    crd: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return adviser profile with their latest snapshot."""
    result = await db.execute(select(Adviser).where(Adviser.crd == crd))
    adviser = result.scalar_one_or_none()
    if adviser is None:
        raise HTTPException(status_code=404, detail="Adviser not found")

    # Latest snapshot
    snap_result = await db.execute(
        select(Snapshot)
        .where(Snapshot.adviser_crd == crd)
        .order_by(Snapshot.period.desc())
        .limit(1)
    )
    latest_snap = snap_result.scalar_one_or_none()

    return {
        "crd": adviser.crd,
        "firm_name": adviser.firm_name,
        "registration_type": adviser.registration_type,
        "sec_number": adviser.sec_number,
        "primary_state": adviser.primary_state,
        "created_at": adviser.created_at.isoformat() if adviser.created_at else None,
        "updated_at": adviser.updated_at.isoformat() if adviser.updated_at else None,
        "latest_snapshot": _snap_dict(latest_snap) if latest_snap else None,
    }


# ---------------------------------------------------------------------------
# GET /advisers/{crd}/history
# ---------------------------------------------------------------------------

@router.get("/{crd}/history")
async def get_adviser_history(
    crd: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all snapshots for an adviser, sorted by period descending."""
    # Verify adviser exists
    result = await db.execute(select(Adviser.crd).where(Adviser.crd == crd))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Adviser not found")

    snap_result = await db.execute(
        select(Snapshot)
        .where(Snapshot.adviser_crd == crd)
        .order_by(Snapshot.period.desc())
    )
    snaps = snap_result.scalars().all()
    return [_snap_dict(s) for s in snaps]


# ---------------------------------------------------------------------------
# GET /advisers/{crd}/changes
# ---------------------------------------------------------------------------

@router.get("/{crd}/changes")
async def get_adviser_changes(
    crd: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all change records for an adviser, sorted by period_to descending."""
    result = await db.execute(select(Adviser.crd).where(Adviser.crd == crd))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Adviser not found")

    change_result = await db.execute(
        select(Change)
        .where(Change.adviser_crd == crd)
        .order_by(Change.period_to.desc(), Change.detected_at.desc())
    )
    changes = change_result.scalars().all()
    return [_change_dict(c) for c in changes]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap_dict(s: Snapshot) -> dict[str, Any]:
    return {
        "id": s.id,
        "adviser_crd": s.adviser_crd,
        "period": s.period,
        "aum": float(s.aum) if s.aum is not None else None,
        "employees": s.employees,
        "num_clients": s.num_clients,
        "registration_status": s.registration_status,
        "ingested_at": s.ingested_at.isoformat() if s.ingested_at else None,
    }


def _change_dict(c: Change) -> dict[str, Any]:
    return {
        "id": c.id,
        "adviser_crd": c.adviser_crd,
        "period_from": c.period_from,
        "period_to": c.period_to,
        "field": c.field,
        "old_value": c.old_value,
        "new_value": c.new_value,
        "detected_at": c.detected_at.isoformat() if c.detected_at else None,
    }
