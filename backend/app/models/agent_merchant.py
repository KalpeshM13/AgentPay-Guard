"""Agent-Merchant association table — maps to blueprint's ``agent_allowlist``.

Each row represents one merchant that a specific agent is *allowed* to pay.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AgentMerchant(Base):
    """Join table implementing the agent ←→ merchant allowlist.

    Ensures an agent can only pay merchants that the owner has explicitly
    approved.  The *agent* and *merchant* pair must be unique.
    """

    __tablename__ = "agent_allowlist"
    __table_args__ = (
        UniqueConstraint("agent_id", "merchant_id", name="uq_agent_merchant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # -- Foreign keys --------------------------------------------------------
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    # -- Relationships -------------------------------------------------------
    agent: Mapped["Agent"] = relationship(back_populates="allowlist_entries")
    merchant: Mapped["Merchant"] = relationship(back_populates="allowlist_entries")

    # -- Timestamp -----------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AgentMerchant agent={self.agent_id} merchant={self.merchant_id}>"
