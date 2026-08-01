from datetime import datetime
from app.db.session import Base

class AuditLog(Base):
    """Immutable event log — never updated, only appended.

    Every policy decision, payment execution, and administrative action
    produces one row here.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "id"):
            self.id = None
        if not hasattr(self, "timestamp"):
            self.timestamp = datetime.now()

        # Convert timestamps from Firestore Timestamp objects
        for attr in ["timestamp"]:
            if hasattr(self, attr):
                v = getattr(self, attr)
                if hasattr(v, "to_datetime"):
                    setattr(self, attr, v.to_datetime())

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} actor={getattr(self, 'actor', None)!r} "
            f"type={getattr(self, 'event_type', None)!r}>"
        )
