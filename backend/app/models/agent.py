from datetime import datetime, timezone
from app.core.constants import AgentStatus
from app.db.session import Base

class Agent(Base):
    """An autonomous AI agent whose spending is controlled by the Policy Server.

    The agent never holds credentials — it can only *request* payments.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if not hasattr(self, "updated_at") or self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
        if not hasattr(self, "id"):
            self.id = None
        if not hasattr(self, "status"):
            self.status = AgentStatus.ACTIVE
        if not hasattr(self, "balance"):
            self.balance = 0.0
        
        # Ensure status is AgentStatus enum type
        if hasattr(self, "status") and isinstance(self.status, str):
            self.status = AgentStatus(self.status)

        # Allowlist relations
        if not hasattr(self, "allowlist_entries"):
            self.allowlist_entries = []

        # Convert timestamps from Firestore Timestamp objects
        for attr in ["created_at", "updated_at"]:
            if hasattr(self, attr):
                v = getattr(self, attr)
                if hasattr(v, "to_datetime"):
                    setattr(self, attr, v.to_datetime())

    @property
    def allowlist(self) -> list:
        """Returns the list of allowlisted Merchant objects associated with this agent."""
        return [entry.merchant for entry in self.allowlist_entries if getattr(entry, 'merchant', None) is not None]

    def to_dict(self) -> dict:
        data = super().to_dict()
        if "status" in data and isinstance(data["status"], AgentStatus):
            data["status"] = data["status"].value
        # Exclude temporary relationship attributes from direct serialization
        data.pop("allowlist_entries", None)
        return data

    def __repr__(self) -> str:
        status_val = self.status.value if isinstance(self.status, AgentStatus) else str(self.status)
        return (
            f"<Agent id={self.id} name={getattr(self, 'name', None)!r} "
            f"status={status_val!r} balance={self.balance}>"
        )
