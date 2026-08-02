"""Central API router — aggregates all endpoint sub-routers.

Registered under ``/api/v1`` in ``app/main.py``.
"""

from fastapi import APIRouter

from app.api.endpoints.agents import router as agents_router
from app.api.endpoints.ai import router as ai_router
from app.api.endpoints.allowlist import router as allowlist_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.merchants import router as merchants_router
from app.api.endpoints.payments import router as payments_router

api_router = APIRouter()

# ---------------------------------------------------------------------------
# Sub-routers
# ---------------------------------------------------------------------------
api_router.include_router(ai_router)
api_router.include_router(dashboard_router)
api_router.include_router(payments_router)
api_router.include_router(agents_router)
api_router.include_router(merchants_router)

# Allowlist is a sub-resource of agents — prefix is "{agent_id}"
api_router.include_router(
    allowlist_router,
    prefix="/agents/{agent_id}/allowlist",
)
