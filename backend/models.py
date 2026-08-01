from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Integer, Table
from sqlalchemy.orm import relationship
from .database import Base

# Many-to-many relationship table for Agent and Allowed Merchants
agent_allowlist = Table(
    "agent_allowlist",
    Base.metadata,
    Column("agent_id", String, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("merchant_id", String, ForeignKey("merchants.id", ondelete="CASCADE"), primary_key=True)
)

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE or FROZEN
    balance = Column(Float, default=10000.0)
    per_tx_limit = Column(Float, default=1000.0)
    daily_limit = Column(Float, default=3000.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    allowlist = relationship(
        "Merchant",
        secondary=agent_allowlist,
        back_populates="allowed_agents"
    )

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, index=True)
    display_name = Column(String, nullable=False)
    destination_reference = Column(String, nullable=False)
    active = Column(Boolean, default=True)

    # Relationships
    allowed_agents = relationship(
        "Agent",
        secondary=agent_allowlist,
        back_populates="allowlist"
    )

class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    request_id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # APPROVED, BLOCKED, PENDING, CANCELLED
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(String, ForeignKey("payment_requests.request_id"), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    settled_at = Column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    actor = Column(String, nullable=False)  # e.g., "AGENT", "OWNER", "SYSTEM"
    event_type = Column(String, nullable=False)  # e.g., "PAYMENT_REQUEST", "FREEZE", "POLICY_UPDATE"
    details = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
