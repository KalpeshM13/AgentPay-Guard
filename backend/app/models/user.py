from datetime import datetime, timezone
from app.core.constants import UserRole
from app.db.session import Base

class User(Base):
    """Owner/operator of the AgentPay Guard platform.

    Every user has a *role* that determines what they can do:
    - ``owner``  — full access: manage agents, policies, other users
    - ``admin``  — manage agents and policies (cannot manage users)
    - ``viewer`` — read-only access to dashboards and logs
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "created_at") or self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if not hasattr(self, "updated_at") or self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
        # Set defaults if not provided
        if not hasattr(self, "id"):
            self.id = None
        if not hasattr(self, "is_active"):
            self.is_active = True
        if not hasattr(self, "role"):
            self.role = UserRole.VIEWER
        
        # Ensure role is UserRole enum type
        if hasattr(self, "role") and isinstance(self.role, str):
            self.role = UserRole(self.role)

        # Convert timestamps from Firestore Timestamp objects
        for attr in ["created_at", "updated_at"]:
            if hasattr(self, attr):
                v = getattr(self, attr)
                if hasattr(v, "to_datetime"):
                    setattr(self, attr, v.to_datetime())

    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.OWNER, UserRole.ADMIN)

    def to_dict(self) -> dict:
        data = super().to_dict()
        if "role" in data and isinstance(data["role"], UserRole):
            data["role"] = data["role"].value
        return data

    def __repr__(self) -> str:
        role_val = self.role.value if isinstance(self.role, UserRole) else str(self.role)
        return f"<User id={self.id} email={getattr(self, 'email', None)!r} role={role_val!r}>"
