"""User ORM model with password hashing.

Uses bcrypt via passlib-alike API for secure password storage.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import UserRole
from app.db.session import Base


class User(Base):
    """Owner/operator of the AgentPay Guard platform.

    Every user has a *role* that determines what they can do:
    - ``owner``  — full access: manage agents, policies, other users
    - ``admin``  — manage agents and policies (cannot manage users)
    - ``viewer`` — read-only access to dashboards and logs
    """

    __tablename__ = "users"

    # -- Columns --------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.VIEWER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # -- repr -----------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value!r}>"

    # -- Properties -----------------------------------------------------------
    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.OWNER, UserRole.ADMIN)
