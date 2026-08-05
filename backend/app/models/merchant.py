from datetime import datetime, timezone
from app.db.session import Base

class Merchant(Base):
    """A counterparty that an agent is allowed (or denied) to pay.

    The ``destination_reference`` is a string that the Payment Executor
    uses to route funds (e.g. an account ID, a vendor code, etc.).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if not hasattr(self, "id"):
            self.id = None
        if not hasattr(self, "active"):
            self.active = True
        if not hasattr(self, "allowlist_entries"):
            self.allowlist_entries = []

        for attr in ["created_at", "updated_at"]:
            if hasattr(self, attr):
                v = getattr(self, attr)
                if hasattr(v, "to_datetime"):
                    setattr(self, attr, v.to_datetime())

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.pop("allowlist_entries", None)
        return data

    def __repr__(self) -> str:
        return f"<Merchant id={self.id} name={getattr(self, 'display_name', None)!r} active={self.active}>"
