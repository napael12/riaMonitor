"""
models.py — SQLAlchemy ORM models matching the database schema in db/init.sql.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Adviser(Base):
    __tablename__ = "advisers"

    crd: Mapped[str] = mapped_column(String(20), primary_key=True)
    firm_name: Mapped[str] = mapped_column(Text, nullable=False)
    registration_type: Mapped[Optional[str]] = mapped_column(String(10))
    sec_number: Mapped[Optional[str]] = mapped_column(String(20))
    primary_state: Mapped[Optional[str]] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    snapshots: Mapped[list["Snapshot"]] = relationship(
        "Snapshot", back_populates="adviser", lazy="selectin"
    )
    changes: Mapped[list["Change"]] = relationship(
        "Change", back_populates="adviser", lazy="selectin"
    )


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (UniqueConstraint("adviser_crd", "period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adviser_crd: Mapped[str] = mapped_column(
        String(20), ForeignKey("advisers.crd", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    aum: Mapped[Optional[float]] = mapped_column(Numeric(20, 2))
    employees: Mapped[Optional[int]] = mapped_column(Integer)
    num_clients: Mapped[Optional[int]] = mapped_column(Integer)
    registration_status: Mapped[Optional[str]] = mapped_column(String(50))
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    adviser: Mapped["Adviser"] = relationship("Adviser", back_populates="snapshots")


class Change(Base):
    __tablename__ = "changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adviser_crd: Mapped[str] = mapped_column(
        String(20), ForeignKey("advisers.crd", ondelete="CASCADE"), nullable=False
    )
    period_from: Mapped[Optional[str]] = mapped_column(String(7))
    period_to: Mapped[Optional[str]] = mapped_column(String(7))
    field: Mapped[Optional[str]] = mapped_column(String(100))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    adviser: Mapped["Adviser"] = relationship("Adviser", back_populates="changes")
