"""Payment Request ORM model — one row per agent payment attempt.

Maps to the blueprint's ``payment_requests`` table (Section 9).
Each request is the record of what the agent asked for and what the
Policy Server + Executor decided.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PaymentRequest(Base):
    """An agent's payment request — accepted, rejected, or pending.

    The ``request_id`` is the client-supplied idempotency key.
    """

    __tablename__ = "payment_requests"

    # -- Identity ------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    request_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True,
        comment="Client-supplied idempotency key (e.g. 'req_1042').",
    )

    # -- Relationships (no cascade — keep the request even if agent deleted) -
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    # -- Payment detail ------------------------------------------------------
    amount: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Requested amount in the simulated currency unit.",
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        comment="PENDING | APPROVED | BLOCKED | SETTLED | CANCELLED.",
    )
    reason: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Rejection reason (e.g. AGENT_FROZEN) when status=BLOCKED.",
    )

    # -- Timestamps ----------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentRequest id={self.id} request_id={self.request_id!r} "
            f"status={self.status!r} amount={self.amount}>"
        )
