"""Merchant ORM model — an approved counterparty an agent can pay.

Maps to the blueprint's ``merchants`` table (Section 9).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Merchant(Base):
    """A counterparty that an agent is allowed (or denied) to pay.

    The ``destination_reference`` is a string that the Payment Executor
    uses to route funds (e.g. an account ID, a vendor code, etc.).
    """

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True,
        comment="Human-readable name, e.g. 'Compute Provider'."
    )
    destination_reference: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Identifier used by the Payment Executor to route funds."
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Optional note about this merchant."
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="When False, the merchant is hidden from new allowlist additions."
    )

    # -- Relationships -------------------------------------------------------
    allowlist_entries: Mapped[list["AgentMerchant"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan",
    )

    # -- Timestamps ----------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Merchant id={self.id} name={self.display_name!r} active={self.active}>"
