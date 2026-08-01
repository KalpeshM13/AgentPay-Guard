"""Agent ORM model — an autonomous AI agent with spend limits and a status.

Maps to the blueprint's ``agents`` table (Section 9).
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AgentStatus
from app.db.session import Base


class Agent(Base):
    """An autonomous AI agent whose spending is controlled by the Policy Server.

    The agent never holds credentials — it can only *request* payments.
    """

    __tablename__ = "agents"

    # -- Identity ------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True,
        comment="Human-readable label, e.g. 'ShoppingAgent-01'."
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Optional free-text description of what this agent does."
    )

    # -- Status (the kill-switch column) -------------------------------------
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False,
        comment="ACTIVE → can request payments; FROZEN → all requests blocked."
    )

    # -- Balance & policy limits ---------------------------------------------
    balance: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
        comment="Simulated wallet balance (non-negative)."
    )
    per_transaction_limit: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Maximum amount allowed per single payment request."
    )
    daily_limit: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Maximum cumulative spend allowed in a calendar day."
    )
    max_requests_per_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10,
        comment="Rate-limit: max payment requests per sliding minute."
    )

    # -- Relationships -------------------------------------------------------
    # allowlist: Mapped[list["Merchant"]] — see association table below
    allowlist_entries: Mapped[list["AgentMerchant"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan",
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
        return (
            f"<Agent id={self.id} name={self.name!r} "
            f"status={self.status.value!r} balance={self.balance}>"
        )
