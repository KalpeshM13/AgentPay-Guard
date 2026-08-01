import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from .database import engine, Base, get_db
from .models import Agent, Merchant, PaymentRequest, Transaction, AuditEvent
from .policy import evaluate_payment_request, get_spent_today
from .payments import execute_payment

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database tables
    Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    # Seed merchants
    if db.query(Merchant).count() == 0:
        merchants = [
            Merchant(id="compute_provider", display_name="Compute Provider Co", destination_reference="acc_112233"),
            Merchant(id="api_provider", display_name="API Provider Corp", destination_reference="acc_445566"),
            Merchant(id="vendor_a", display_name="Vendor A", destination_reference="acc_778899"),
            Merchant(id="aws_demo", display_name="AWS Cloud Services", destination_reference="acc_aws101"),
        ]
        for m in merchants:
            db.add(m)
        db.commit()

    # Seed default Agent-01
    if db.query(Agent).count() == 0:
        agent = Agent(
            id="agent_01",
            name="ShoppingAgent-01",
            status="ACTIVE",
            balance=10000.0,
            per_tx_limit=1000.0,
            daily_limit=3000.0
        )
        # Default allowlisted merchants
        compute = db.query(Merchant).filter(Merchant.id == "compute_provider").first()
        api_prov = db.query(Merchant).filter(Merchant.id == "api_provider").first()
        vendor_a = db.query(Merchant).filter(Merchant.id == "vendor_a").first()
        
        if compute:
            agent.allowlist.append(compute)
        if api_prov:
            agent.allowlist.append(api_prov)
        if vendor_a:
            agent.allowlist.append(vendor_a)
            
        db.add(agent)
        db.commit()
    db.close()
    yield

app = FastAPI(title="AgentPay Guard API", version="1.0.0", lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class PaymentRequestSchema(BaseModel):
    request_id: str = Field(..., description="Unique transaction/request identifier")
    agent_id: str = Field(..., description="ID of the requesting agent")
    merchant_id: str = Field(..., description="ID of the counterparty/merchant")
    amount: float = Field(..., gt=0, description="Amount to be paid")

class PolicyUpdateSchema(BaseModel):
    per_tx_limit: float = Field(..., gt=0)
    daily_limit: float = Field(..., gt=0)

class AllowlistUpdateSchema(BaseModel):
    merchant_id: str = Field(...)
    display_name: str | None = Field(None)
    destination_reference: str | None = Field(None)


@app.post("/payments")
def process_payment(req: PaymentRequestSchema, db: Session = Depends(get_db)):
    """
    Endpoint for Agents to request payments.
    Independently validates rules, logs requests, and executes settlement if valid.
    """
    # 1. Run Policy Check
    is_approved, reason = evaluate_payment_request(
        db, req.agent_id, req.merchant_id, req.amount, req.request_id
    )

    if reason == "DUPLICATE_REQUEST":
        raise HTTPException(status_code=400, detail={"status": "BLOCKED", "reason": reason})

    # 2. Log request in history
    db_request = PaymentRequest(
        request_id=req.request_id,
        agent_id=req.agent_id,
        merchant_id=req.merchant_id,
        amount=req.amount,
        status="APPROVED" if is_approved else "BLOCKED",
        reason=reason if not is_approved else None,
        created_at=datetime.utcnow()
    )
    db.add(db_request)
    db.commit()

    # 3. Handle Audit log for requests
    audit = AuditEvent(
        actor="AGENT",
        event_type="PAYMENT_REQUEST",
        details=f"Payment request {req.request_id} for Rs {req.amount} to merchant '{req.merchant_id}' -> Status: {db_request.status} (Reason: {reason})",
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()

    if not is_approved:
        raise HTTPException(status_code=400, detail={"status": "BLOCKED", "reason": reason})

    # 4. Settle / Execute Payment
    success, message = execute_payment(db, req.agent_id, req.amount, req.request_id)
    if not success:
        # Revert status to BLOCKED or handle failure
        db_request.status = "BLOCKED"
        db_request.reason = message
        db.commit()
        raise HTTPException(status_code=500, detail={"status": "BLOCKED", "reason": message})

    # Get remaining daily allowance
    agent = db.query(Agent).filter(Agent.id == req.agent_id).first()
    spent_today = get_spent_today(db, req.agent_id)
    remaining_daily = max(0.0, agent.daily_limit - spent_today)

    return {
        "status": "APPROVED",
        "remaining_daily_limit": remaining_daily,
        "balance": agent.balance
    }


@app.post("/agents/{id}/freeze")
def freeze_agent(id: str, db: Session = Depends(get_db)):
    """Owner endpoint to freeze the agent instantly (Kill Switch)."""
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.status = "FROZEN"
    
    audit = AuditEvent(
        actor="OWNER",
        event_type="FREEZE",
        details=f"Agent '{id}' frozen by owner switch.",
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": f"Agent {id} frozen successfully"}


@app.post("/agents/{id}/unfreeze")
def unfreeze_agent(id: str, db: Session = Depends(get_db)):
    """Owner endpoint to unfreeze the agent."""
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.status = "ACTIVE"
    
    audit = AuditEvent(
        actor="OWNER",
        event_type="UNFREEZE",
        details=f"Agent '{id}' unfrozen by owner switch.",
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": f"Agent {id} unfrozen successfully"}


@app.put("/agents/{id}/policy")
def update_policy(id: str, policy: PolicyUpdateSchema, db: Session = Depends(get_db)):
    """Owner endpoint to update transaction and daily limit policies."""
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.per_tx_limit = policy.per_tx_limit
    agent.daily_limit = policy.daily_limit
    
    audit = AuditEvent(
        actor="OWNER",
        event_type="POLICY_UPDATE",
        details=f"Agent '{id}' policy updated: per_tx_limit=Rs {policy.per_tx_limit}, daily_limit=Rs {policy.daily_limit}",
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": "Policy updated successfully"}


@app.post("/agents/{id}/allowlist")
def add_to_allowlist(id: str, payload: AllowlistUpdateSchema, db: Session = Depends(get_db)):
    """Owner endpoint to add a merchant to an agent's allowlist."""
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    merchant = db.query(Merchant).filter(Merchant.id == payload.merchant_id).first()
    if not merchant:
        # Create merchant dynamically if it doesn't exist
        display_name = payload.display_name or payload.merchant_id.replace("_", " ").title()
        destination_reference = payload.destination_reference or f"acc_{payload.merchant_id}"
        merchant = Merchant(
            id=payload.merchant_id,
            display_name=display_name,
            destination_reference=destination_reference
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
    else:
        if payload.display_name:
            merchant.display_name = payload.display_name
        if payload.destination_reference:
            merchant.destination_reference = payload.destination_reference
        db.commit()
        
    if merchant not in agent.allowlist:
        agent.allowlist.append(merchant)
        
        audit = AuditEvent(
            actor="OWNER",
            event_type="ALLOWLIST_ADD",
            details=f"Merchant '{payload.merchant_id}' added to agent '{id}' allowlist.",
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        
    return {"status": "success", "message": f"Merchant {payload.merchant_id} allowlisted"}


@app.delete("/agents/{id}/allowlist/{merchant_id}")
def remove_from_allowlist(id: str, merchant_id: str, db: Session = Depends(get_db)):
    """Owner endpoint to remove a merchant from an agent's allowlist."""
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
        
    if merchant in agent.allowlist:
        agent.allowlist.remove(merchant)
        
        audit = AuditEvent(
            actor="OWNER",
            event_type="ALLOWLIST_REMOVE",
            details=f"Merchant '{merchant_id}' removed from agent '{id}' allowlist.",
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        
    return {"status": "success", "message": f"Merchant {merchant_id} removed from allowlist"}


@app.get("/agents/{id}")
def get_agent_details(id: str, db: Session = Depends(get_db)):
    """Gets current agent status, settings, balance, and list of approved merchants."""
    agent = db.query(Agent).filter(Agent.id == id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    spent_today = get_spent_today(db, id)
    remaining_daily = max(0.0, agent.daily_limit - spent_today)
    
    return {
        "id": agent.id,
        "name": agent.name,
        "status": agent.status,
        "balance": agent.balance,
        "per_tx_limit": agent.per_tx_limit,
        "daily_limit": agent.daily_limit,
        "spent_today": spent_today,
        "remaining_daily_limit": remaining_daily,
        "allowlist": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "destination_reference": m.destination_reference
            } for m in agent.allowlist
        ]
    }


@app.get("/agents/{id}/transactions")
def get_agent_transactions(id: str, db: Session = Depends(get_db)):
    """Loads transaction history feed for a specific agent."""
    requests = db.query(PaymentRequest).filter(PaymentRequest.agent_id == id).order_by(PaymentRequest.created_at.desc()).all()
    
    feed = []
    for r in requests:
        # Check if transaction was settled
        tx = db.query(Transaction).filter(Transaction.request_id == r.request_id).first()
        feed.append({
            "request_id": r.request_id,
            "merchant_id": r.merchant_id,
            "amount": r.amount,
            "status": r.status,
            "reason": r.reason,
            "created_at": r.created_at,
            "settled_at": tx.settled_at if tx else None,
        })
    return feed
