from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Agent, Merchant, PaymentRequest, Transaction

def check_duplicate_request(db: Session, request_id: str) -> bool:
    """Returns True if a request_id has already been processed."""
    existing = db.query(PaymentRequest).filter(PaymentRequest.request_id == request_id).first()
    return existing is not None

def check_rate_limit(db: Session, agent_id: str, limit_per_minute: int = 5) -> bool:
    """Returns True if the agent has sent more than `limit_per_minute` requests in the last minute."""
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    request_count = db.query(PaymentRequest).filter(
        PaymentRequest.agent_id == agent_id,
        PaymentRequest.created_at >= one_minute_ago
    ).count()
    return request_count >= limit_per_minute

def get_spent_today(db: Session, agent_id: str) -> float:
    """Calculates the sum of APPROVED payments today (UTC)."""
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    # Sum up all successful transactions today
    transactions = db.query(Transaction).join(
        PaymentRequest, Transaction.request_id == PaymentRequest.request_id
    ).filter(
        PaymentRequest.agent_id == agent_id,
        Transaction.settled_at >= start_of_day
    ).all()
    
    return sum(tx.amount for tx in transactions)

def evaluate_payment_request(db: Session, agent_id: str, merchant_id: str, amount: float, request_id: str) -> tuple[bool, str]:
    """
    Evaluates policy checks for a payment request.
    Returns (is_approved, reason).
    """
    # 1. Replay Protection
    if check_duplicate_request(db, request_id):
        return False, "DUPLICATE_REQUEST"

    # Load agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return False, "AGENT_NOT_FOUND"

    # 2. Frozen/Kill Switch Check
    if agent.status == "FROZEN":
        return False, "AGENT_FROZEN"

    # Load merchant
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id, Merchant.active == True).first()
    if not merchant:
        return False, "MERCHANT_NOT_FOUND"

    # 3. Merchant Allowlist Check
    if merchant not in agent.allowlist:
        return False, "MERCHANT_NOT_ALLOWED"

    # 4. Per-transaction Limit Check
    if amount > agent.per_tx_limit:
        return False, "PER_TX_LIMIT_EXCEEDED"

    # 5. Daily Cumulative Limit Check
    spent_today = get_spent_today(db, agent_id)
    if spent_today + amount > agent.daily_limit:
        return False, "DAILY_LIMIT_EXCEEDED"

    # 6. Rate Limit / Velocity Check
    # Default limit is 5 requests per minute
    if check_rate_limit(db, agent_id, limit_per_minute=5):
        return False, "RATE_LIMIT_EXCEEDED"

    # 7. Check Sufficient Funds (Agent Balance)
    if amount > agent.balance:
        return False, "INSUFFICIENT_FUNDS"

    return True, "APPROVED"
