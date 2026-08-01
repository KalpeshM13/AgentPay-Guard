"""Audit Log ORM model — immutable record of every significant event.

Maps to the blueprint's ``audit_events`` table (Section 9).
Every policy decision, payment execution, and administrative action
produces one row here.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditLog(Base):
    """Immutable event log — never updated, only appended."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # -- Who / what ----------------------------------------------------------
    actor: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="Who triggered the event (agent_id, user_email, or 'system').",
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="Categorisation: payment_approved, agent_frozen, etc.",
    )

    # -- What happened -------------------------------------------------------
    details: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Free-form JSON or text describing the event payload.",
    )

    # -- Timestamp -----------------------------------------------------------
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} actor={self.actor!r} "
            f"type={self.event_type!r}>"
        )
