import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.models import Agent, Merchant

# Setup a temporary file SQLite DB for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///test_policy.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override database dependency in FastAPI app
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Add dummy merchants
    m1 = Merchant(id="aws_demo", display_name="AWS Demo", destination_reference="acc_aws")
    m2 = Merchant(id="unknown_merchant", display_name="Scammer Shop", destination_reference="acc_bad")
    db.add_all([m1, m2])
    db.commit()

    # Add dummy agent
    agent = Agent(
        id="test_agent",
        name="Test Agent",
        status="ACTIVE",
        balance=5000.0,
        per_tx_limit=1000.0,
        daily_limit=2000.0
    )
    agent.allowlist.append(m1)
    db.add(agent)
    db.commit()
    db.close()
    
    yield
    
    # Tear down tables
    Base.metadata.drop_all(bind=engine)

def test_successful_payment():
    response = client.post(
        "/payments",
        json={
            "request_id": "req_001",
            "agent_id": "test_agent",
            "merchant_id": "aws_demo",
            "amount": 300.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"
    assert data["balance"] == 4700.0
    assert data["remaining_daily_limit"] == 1700.0

def test_payment_exceeds_per_tx_limit():
    response = client.post(
        "/payments",
        json={
            "request_id": "req_002",
            "agent_id": "test_agent",
            "merchant_id": "aws_demo",
            "amount": 1500.0
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "PER_TX_LIMIT_EXCEEDED"

def test_payment_not_allowlisted_merchant():
    response = client.post(
        "/payments",
        json={
            "request_id": "req_003",
            "agent_id": "test_agent",
            "merchant_id": "unknown_merchant",
            "amount": 100.0
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "MERCHANT_NOT_ALLOWED"

def test_agent_frozen_switch():
    # Freeze agent
    freeze_resp = client.post("/agents/test_agent/freeze")
    assert freeze_resp.status_code == 200
    
    # Request payment
    response = client.post(
        "/payments",
        json={
            "request_id": "req_004",
            "agent_id": "test_agent",
            "merchant_id": "aws_demo",
            "amount": 200.0
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "AGENT_FROZEN"

    # Unfreeze and retry
    unfreeze_resp = client.post("/agents/test_agent/unfreeze")
    assert unfreeze_resp.status_code == 200
    
    response2 = client.post(
        "/payments",
        json={
            "request_id": "req_004", # Re-using request_id will trigger replay protection, let's use a new one
            "agent_id": "test_agent",
            "merchant_id": "aws_demo",
            "amount": 200.0
        }
    )
    assert response2.status_code == 400
    assert response2.json()["detail"]["reason"] == "DUPLICATE_REQUEST"

    response3 = client.post(
        "/payments",
        json={
            "request_id": "req_005",
            "agent_id": "test_agent",
            "merchant_id": "aws_demo",
            "amount": 200.0
        }
    )
    assert response3.status_code == 200
    assert response3.json()["status"] == "APPROVED"

def test_daily_cumulative_limit():
    # Tx 1: 900 (success)
    client.post(
        "/payments",
        json={"request_id": "req_101", "agent_id": "test_agent", "merchant_id": "aws_demo", "amount": 900.0}
    )
    # Tx 2: 900 (success)
    client.post(
        "/payments",
        json={"request_id": "req_102", "agent_id": "test_agent", "merchant_id": "aws_demo", "amount": 900.0}
    )
    # Tx 3: 300 (should fail because 900+900+300 = 2100 > 2000 daily limit)
    response = client.post(
        "/payments",
        json={"request_id": "req_103", "agent_id": "test_agent", "merchant_id": "aws_demo", "amount": 300.0}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["reason"] == "DAILY_LIMIT_EXCEEDED"
