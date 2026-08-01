from datetime import datetime, timezone
from app.db.session import Base

class AgentMerchant(Base):
    """Join table implementing the agent ←→ merchant allowlist.

    Ensures an agent can only pay merchants that the owner has explicitly
    approved.  The *agent* and *merchant* pair must be unique.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if not hasattr(self, "id"):
            self.id = None
        if not hasattr(self, "agent"):
            self.agent = None
        if not hasattr(self, "merchant"):
            self.merchant = None

        # Convert timestamps from Firestore Timestamp objects
        for attr in ["created_at"]:
            if hasattr(self, attr):
                v = getattr(self, attr)
                if hasattr(v, "to_datetime"):
                    setattr(self, attr, v.to_datetime())

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.pop("agent", None)
        data.pop("merchant", None)
        return data

    def __repr__(self) -> str:
        return f"<AgentMerchant agent={getattr(self, 'agent_id', None)} merchant={getattr(self, 'merchant_id', None)}>"
