"""Firebase database session wrapper.

Provides a simple base class for models and a FastAPI dependency that yields a Firebase client.
"""

from app.db.firebase import FirebaseClient

# ---------------------------------------------------------------------------
# Declarative Base Mock
# ---------------------------------------------------------------------------
class Base:
    """Base class for all models, replacing SQLAlchemy DeclarativeBase."""
    
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    def to_dict(self) -> dict:
        data = {}
        for key, val in self.__dict__.items():
            if not key.startswith("_"):
                data[key] = val
        return data

# ---------------------------------------------------------------------------
# FastAPI dependency – yields a FirebaseClient
# ---------------------------------------------------------------------------
async def get_session():
    """FastAPI dependency that provides a FirebaseClient database session."""
    yield FirebaseClient()
