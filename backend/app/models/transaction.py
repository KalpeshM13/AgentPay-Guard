from datetime import datetime
from app.db.session import Base

class Transaction(Base):
    """A settled payment — the simulated wallet's ledger entry.

    ``balance_before`` and ``balance_after`` form an immutable audit trail
    of the agent's wallet at the time of settlement.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "id"):
            self.id = None
        if not hasattr(self, "settled_at"):
            self.settled_at = datetime.now()

        for attr in ["settled_at"]:
            if hasattr(self, attr):
                v = getattr(self, attr)
                if hasattr(v, "to_datetime"):
                    setattr(self, attr, v.to_datetime())

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} agent={getattr(self, 'agent_id', None)} "
            f"amount={getattr(self, 'amount', None)} before={getattr(self, 'balance_before', None)} "
            f"after={getattr(self, 'balance_after', None)}>"
        )
