"""
routers/changes.py — Changes feed API endpoints.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Change

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("")
async def list_changes(
    period: Optional[str] = Query(None, description="Filter by period (YYYY-MM)"),
    field: Optional[str] = Query(None, description="Filter by changed field name"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return recent changes across all advisers.

    Query parameters:
    - **period**: Filter to changes whose period_to equals this value (YYYY-MM).
    - **field**: Filter to changes for a specific field (e.g. ``aum``, ``employees``).
    - **limit**: Maximum number of rows to return (default 100, max 1000).
    - **offset**: Pagination offset.
    """
    from sqlalchemy import func

    stmt = select(Change)

    if period:
        stmt = stmt.where(Change.period_to == period)
    if field:
        stmt = stmt.where(Change.field == field)

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginate — newest first
    stmt = (
        stmt.order_by(Change.period_to.desc(), Change.detected_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    changes = result.scalars().all()

    items = [
        {
            "id": c.id,
            "adviser_crd": c.adviser_crd,
            "period_from": c.period_from,
            "period_to": c.period_to,
            "field": c.field,
            "old_value": c.old_value,
            "new_value": c.new_value,
            "detected_at": c.detected_at.isoformat() if c.detected_at else None,
        }
        for c in changes
    ]

    return {"total": total, "items": items, "offset": offset, "limit": limit}
