from datetime import datetime
from sqlalchemy.orm import Session
from .models import Agent, Transaction, PaymentRequest, AuditEvent

def execute_payment(db: Session, agent_id: str, amount: float, request_id: str) -> tuple[bool, str]:
    """
    Executes a payment after it has been approved.
    Deducts balance, registers the transaction, and returns (success, detail).
    """
    # Load agent with lock for thread safety
    agent = db.query(Agent).filter(Agent.id == agent_id).with_for_update().first()
    if not agent:
        return False, "Agent not found"

    if agent.balance < amount:
        return False, "Insufficient funds"

    balance_before = agent.balance
    agent.balance -= amount
    balance_after = agent.balance

    # Create Transaction record
    transaction = Transaction(
        request_id=request_id,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        settled_at=datetime.utcnow()
    )
    db.add(transaction)

    # Create Audit Event
    audit_event = AuditEvent(
        actor="SYSTEM",
        event_type="PAYMENT_SETTLED",
        details=f"Settled payment for {agent_id}. Amount: Rs {amount}. Balance: Rs {balance_before} -> Rs {balance_after}",
        timestamp=datetime.utcnow()
    )
    db.add(audit_event)

    db.commit()
    return True, "Payment settled successfully"
