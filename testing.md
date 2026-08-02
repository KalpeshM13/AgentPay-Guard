# AgentPay Guard - Step-by-Step Testing Guide

This document provides a comprehensive step-by-step guide for testing **AgentPay Guard**, covering the **Backend (FastAPI)**, **Smart Contracts (Hardhat)**, and **Frontend Dashboard (React/Vite)**.

---

## 📋 Prerequisites & Environment Setup

Before starting the testing process, ensure you have the following installed:
- **Node.js** (v18 or higher)
- **Python** (v3.10 or higher)
- **npm** or **pnpm**
- **Git**

---

## 🛠️ Step 1: Backend Testing (FastAPI & Policy Engine)

### 1.1 Setup Virtual Environment & Install Dependencies
Open a terminal and navigate to the `backend` folder:
```bash
cd backend
```

Create and activate Python Virtual Environment:
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r requirements.txt
```

### 1.2 Start Backend Server
Run the FastAPI development server:
```bash
uvicorn app.main:app --reload --port 8000
```
- **Server URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

### 1.3 Interactive API Testing (via Swagger UI)
Open `http://127.0.0.1:8000/docs` in your browser to test core endpoints:

1. **Health Check**:
   - Execute `GET /health` or `GET /` -> Expect `200 OK`.
2. **Create / Fetch Agent**:
   - Execute `GET /api/v1/agents` or `POST /api/v1/agents` to view active agents and spend limits.
3. **Test Payment Policy Engine**:
   - `POST /api/v1/payments` with payload:
     ```json
     {
       "agent_id": 1,
       "merchant_id": "merchant_aws_01",
       "amount": 50.0,
       "request_id": "req_test_001"
     }
     ```
   - **Expected**: `200 OK` (Approved & Settled) if within limits and merchant is allowlisted.

---

## ⛓️ Step 2: Smart Contracts Testing (Hardhat & Web3)

### 2.1 Compile Contracts
Open a new terminal window and navigate to `contracts/`:
```bash
cd contracts
```

Compile the Solidity smart contracts:
```bash
npx hardhat compile
```
- **Expected Output**: `Compiled 1 Solidity file successfully` or `Nothing to compile`.

### 2.2 Launch Local Blockchain Node
Start a local Hardhat Ethereum node:
```bash
npx hardhat node
```
- **Local Network**: `http://127.0.0.1:8545`
- Note down the pre-funded test accounts and private keys displayed in the terminal.

### 2.3 Deploy Contracts to Local Network
In a separate terminal, deploy `AgentGuardWallet.sol` to the running local node:
```bash
npx hardhat run scripts/deploy.js --network localhost
```
- **Expected Output**: Contract deployed address (e.g., `0x5FbDB2315678afecb367f032d93F642f64180aa3`).

### 2.4 Automated Contract Testing
Run Hardhat test suite:
```bash
npx hardhat test
```

---

## 💻 Step 3: Frontend Testing (React / Vite Dashboard)

### 3.1 Setup & Build Frontend
Open a terminal window and navigate to `frontend/`:
```bash
cd frontend
```

Install dependencies:
```bash
npm install
```

Verify production build compilation:
```bash
npm run build
```
- **Expected Output**: `built in ...ms` without errors.

### 3.2 Launch Frontend Development Server
Start the dev server:
```bash
npm run dev
```
- **Local Application URL**: `http://localhost:5173/`

### 3.3 Dashboard Manual UI Testing Checklist
1. **Agent Overview**: Verify agent status (`ACTIVE`), current balance, per-transaction limit, and daily spend limit display correctly.
2. **Merchant Allowlist Management**: Try adding/removing allowlisted merchants.
3. **Payment Request Simulation**: Trigger a payment request and check if real-time balance and transaction history update.
4. **Kill Switch / Freeze Test**: Click the **FREEZE** button for an agent. Verify that the agent badge turns red/frozen, and subsequent payment requests are blocked instantly.

---

## 🧪 Step 4: Security & Attack Scenario Test Matrix

Execute the following test cases to ensure the security invariants hold:

| Test Case # | Scenario | Action | Expected Result |
| :--- | :--- | :--- | :--- |
| **TC-01** | **Normal Payment** | Send payment request within limit to allowlisted merchant. | **APPROVED** - Transaction recorded & wallet debited. |
| **TC-02** | **Per-Tx Limit Violation** | Send payment amount exceeding single transaction limit. | **REJECTED** - Blocked by policy engine (`Per-transaction limit exceeded`). |
| **TC-03** | **Daily Limit Exceeded** | Send multiple payments that cumulatively exceed daily limit. | **REJECTED** - Blocked by policy engine (`Daily spending limit exceeded`). |
| **TC-04** | **Unapproved Merchant** | Request payment for a merchant not on the allowlist. | **REJECTED** - Blocked (`Merchant not allowlisted`). |
| **TC-05** | **Agent Freeze (Kill Switch)** | Press **FREEZE** on Owner Dashboard, then send payment. | **REJECTED** - Blocked immediately (`Agent is FROZEN`). |
| **TC-06** | **Replay Attack** | Re-send payment with identical `request_id`. | **REJECTED** - Blocked (`Duplicate request ID`). |

---

## ❓ Troubleshooting & FAQs

- **Port 8000 or 5173 already in use**:
  - Kill process occupying the port or run uvicorn on an alternate port:
    ```bash
    uvicorn app.main:app --reload --port 8001
    ```
- **Database Reset**:
  - If using SQLite locally and you want a clean state, delete `backend/data/agentpay.db` (or restart the backend server to re-initialize).
- **Environment Variables**:
  - Ensure `.env` in `backend/` matches your environment setup (refer to `.env.example`).
