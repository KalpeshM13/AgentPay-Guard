"""Authentication service — password hashing, JWT creation, and user CRUD using Firestore.

This is the *only* module that touches bcrypt and jose libraries.
"""

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


# =============================================================================
# Password hashing (bcrypt)
# =============================================================================

def hash_password(plain: str) -> str:
    """Hash a plain-text password with a per-password random salt.

    Returns a bcrypt hash string (e.g. ``$2b$12$...``).
    """
    return bcrypt.hashpw(
        plain.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    return bcrypt.checkpw(
        plain.encode("utf-8"), hashed.encode("utf-8")
    )


# =============================================================================
# JWT token utilities
# =============================================================================

def create_access_token(user_id: int) -> tuple[str, int]:
    """Create a signed JWT access token for *user_id*.

    Returns ``(token, expires_in_seconds)``.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    expires_in = int(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return token, expires_in


def decode_access_token(token: str) -> int | None:
    """Decode and validate a JWT, returning the ``user_id`` or ``None``.

    Returns ``None`` when the token is expired, malformed, or the signature
    does not match.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except JWTError:
        return None


# =============================================================================
# User database operations (Firestore)
# =============================================================================

async def get_user_by_id(session: any, user_id: int) -> User | None:
    """Fetch a user by primary key."""
    data = await session.get("users", user_id)
    if data:
        return User(**data)
    return None


async def get_user_by_email(session: any, email: str) -> User | None:
    """Fetch a user by email (case-insensitive)."""
    email_normalized = email.lower().strip()
    results = await session.query("users", [("email", "==", email_normalized)])
    if results:
        return User(**results[0])
    return None


async def register_user(
    session: any,
    email: str,
    plain_password: str,
    display_name: str,
) -> User:
    """Create a new user in Firestore with a bcrypt-hashed password.

    The caller **must** have checked that the email is not already taken.
    """
    next_id = await session.get_next_id("users")
    user = User(
        id=next_id,
        email=email.lower().strip(),
        hashed_password=hash_password(plain_password),
        display_name=display_name.strip(),
        role="owner",
        is_active=True,
        balance=10.0,
    )
    await session.insert("users", next_id, user.to_dict())
    logger.info("User registered in Firestore: id=%d email=%s role=%s", user.id, user.email, user.role)

    # Auto-create default agent for this user
    try:
        from app.services.agent_service import create_agent
        from app.services.allowlist_service import add_to_allowlist
        from app.models.merchant import Merchant

        # Clean display name for agent name (alphanumeric + underscore/hyphen)
        clean_name = "".join(c for c in user.display_name if c.isalnum() or c in ("-", "_")).strip()
        if not clean_name:
            clean_name = "User"
        agent_name = f"Agent-{clean_name}"

        agent = await create_agent(
            session,
            name=agent_name,
            description="Default autonomous spending agent",
            balance=10.0,
            per_transaction_limit=1.0,
            daily_limit=5.0,
            max_requests_per_minute=10,
            user_id=user.id,
        )

        # Seed allowlist with default merchants (1, 2, 3, 4)
        for mid in [1, 2, 3, 4]:
            m_data = await session.get("merchants", mid)
            if m_data:
                merchant = Merchant(**m_data)
                await add_to_allowlist(session, agent, merchant)
    except Exception as e:
        logger.error(f"Failed to auto-create default agent/allowlist for user {user.id}: {e}")

    return user


async def authenticate_user(
    session: any, email: str, plain_password: str
) -> User | None:
    """Verify credentials and return the User, or ``None`` on failure."""
    user = await get_user_by_email(session, email)
    if user is None:
        return None
    if not getattr(user, "is_active", True):
        logger.warning("Login attempt for inactive user id=%d", user.id)
        return None
    if not verify_password(plain_password, getattr(user, "hashed_password", "")):
        return None
    return user
