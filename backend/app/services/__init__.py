"""Business logic services package."""

# -- Agent CRUD ----------------------------------------------------------------
from app.services.agent_service import (  # noqa: F401
    create_agent,
    delete_agent,
    freeze_agent,
    get_agent_by_id,
    get_agent_by_name,
    list_agents,
    unfreeze_agent,
    update_agent,
)

# -- AI explainability (optional) ----------------------------------------------
from app.services.ai_service import (  # noqa: F401
    explain_blocked_payment,
    explain_policy,
    summarize_audit,
)

# -- Allowlist management ------------------------------------------------------
from app.services.allowlist_service import (  # noqa: F401
    add_to_allowlist,
    get_allowlist_entry,
    list_allowlist,
    remove_from_allowlist,
)

# -- Dashboard (read-only queries) ---------------------------------------------
from app.services.dashboard_service import (  # noqa: F401
    get_activity,
    get_audit,
    get_summary,
)

# -- Merchant CRUD -------------------------------------------------------------
from app.services.merchant_service import (  # noqa: F401
    create_merchant,
    delete_merchant,
    get_merchant_by_id,
    get_merchant_by_name,
    list_merchants,
)

# -- Payment Executor ----------------------------------------------------------
from app.services.payment_executor import (  # noqa: F401
    count_recent_requests,
    execute,
    get_daily_spend,
    is_duplicate_request_id,
)

# -- Policy Engine -------------------------------------------------------------
from app.services.policy_engine import (  # noqa: F401
    PolicyContext,
    PolicyDecision,
    evaluate,
)
