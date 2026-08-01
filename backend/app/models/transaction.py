"""Transaction ORM model — one row for every *settled* payment.

Maps to the blueprint's ``transactions`` table (Section 9).
A transaction is only created after the Payment Executor successfully
debits the agent's balance.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Transaction(Base):
    """A settled payment — the simulated wallet's ledger entry.

    ``balance_before`` and ``balance_after`` form an immutable audit trail
    of the agent's wallet at the time of settlement.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # -- Link back to the approved request -----------------------------------
    request_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("payment_requests.request_id"), nullable=False,
        index=True,
        comment="Links back to the approved PaymentRequest.",
    )
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    # -- Financial detail ----------------------------------------------------
    amount: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Debited amount.",
    )
    balance_before: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Agent balance before the debit.",
    )
    balance_after: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Agent balance after the debit.",
    )

    # -- Timestamp -----------------------------------------------------------
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} agent={self.agent_id} "
            f"amount={self.amount} before={self.balance_before} "
            f"after={self.balance_after}>"
        )
