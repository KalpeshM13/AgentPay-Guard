from datetime import datetime
from app.db.session import Base

class PaymentRequest(Base):
    """An agent's payment request — accepted, rejected, or pending.

    The ``request_id`` is the client-supplied idempotency key.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "id"):
            self.id = None
        if not hasattr(self, "created_at"):
            self.created_at = datetime.now()

        for attr in ["created_at"]:
            if hasattr(self, attr):
                v = getattr(self, attr)
                if hasattr(v, "to_datetime"):
                    setattr(self, attr, v.to_datetime())

    def __repr__(self) -> str:
        return (
            f"<PaymentRequest id={self.id} request_id={getattr(self, 'request_id', None)!r} "
            f"status={getattr(self, 'status', None)!r} amount={getattr(self, 'amount', None)}>"
        )
