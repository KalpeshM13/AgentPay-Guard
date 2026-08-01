# AgentPay Guard

> **Kill Switch & Policy-Enforced Payments for Autonomous AI Agents**

AgentPay Guard is a payment-control layer for autonomous AI agents. Instead of trusting an agent to obey spending rules via internal system prompts or inline code constraints (which are prone to jailbreaks, bugs, or prompt-injection attacks), every payment request is routed through an independent backend that owns the payment credentials and enforces predefined financial policies. The agent cannot change those policies or bypass the backend.

---

## 1. Executive Summary

| Requirement | How AgentPay Guard satisfies it |
| :--- | :--- |
| **Wallet/contract-level independent enforcement** | A trusted Policy Server sits between the agent and the payment executor; only the server can move funds. |
| **Spend limits** | Per-transaction, daily cumulative, and optional velocity limits are checked before execution. |
| **Allowlisted counterparties** | Payments are accepted only for owner-approved merchant IDs/accounts. |
| **Owner kill switch** | Owner dashboard changes agent status to `FROZEN`; all subsequent payment requests fail instantly. |
| **Attack resistance** | Overspend, unknown merchant, split-payment, replay/rate-limit, and frozen-agent attempts are rejected. |
| **In-flight revocation (Bonus)** | High-risk payments enter a short `PENDING` state and are rechecked before final execution. |
| **Real-world plausibility** | The simulated wallet can later be replaced with a sandbox payment provider without changing the policy architecture. |

---

## 2. Security Invariant

> **The AI agent never possesses the bank/payment-provider secret key, API key, or unrestricted wallet credential.**

---

## 3. Product Concept

The system consists of five logical parts:
1. **AI Agent**: Decides what it wants to buy/pay for and sends a payment request.
2. **Policy Server**: Independently validates status, counterparty, amount, cumulative spend, and velocity.
3. **Payment Executor**: The only component allowed to debit the simulated/real account.
4. **Owner Dashboard**: Configures limits, manages allowlists, monitors activity, and freezes/unfreezes the agent.
5. **Database/Audit Log**: Stores agents, policies, counterparties, requests, decisions, and timestamps.

---

## 4. High-Level Architecture

```
HUMAN OWNER
     │
     │ set limits / allowlist / FREEZE
     ▼
OWNER DASHBOARD
     │
     ▼
POLICY SERVER <───────────────── AI AGENT
     │                               │
     │ checks every request          │ POST /payments
     │
     ├── status active?
     ├── merchant allowed?
     ├── per-tx limit?
     ├── daily limit?
     └── rate/velocity limit?
     │
 [ PASS / FAIL ]
     │
     ├─── FAIL ────> Audit log + BLOCK
     │
    PASS
     ▼
PAYMENT EXECUTOR
     │
     ▼
SIMULATED WALLET / PAYMENT SANDBOX
     │
     ▼
TRANSACTION + AUDIT LOG
```

---

## 5. Recommended Beginner Tech Stack

*   **Agent**: Python (easy scripting, API calls, and LLM integration).
*   **Backend/API**: FastAPI (simple REST endpoints, automatic API docs, Python-native).
*   **Database**: SQLite + SQLAlchemy (zero setup, ideal for hackathon MVP).
*   **Dashboard**: Streamlit (fastest way to build a working Python UI).
*   **Payment Layer**: Simulated wallet first (no financial onboarding, deterministic demo).
*   **LLM**: Optional LLM API (add only after transaction controls work).
*   **Testing**: `pytest` / simple scripts (to automate attack scenarios).
*   **Deployment**: Localhost initially.

---

## 6. MVP Scope vs. Stretch Scope

| MVP (Build this first) | Stretch (Only if MVP works) |
| :--- | :--- |
| Per-transaction limit | Hourly/velocity limits |
| Daily cumulative limit | Automatic anomaly-triggered freeze |
| Merchant allowlist | Risk score |
| Manual freeze/unfreeze | Multiple agents with separate policies |
| Transaction log | Role-based owner/admin access |
| Simulated balance | Payment-provider sandbox |
| Attack demo | Pending payments / in-flight revocation |

---

## 7. End-to-End Workflow

1. Owner creates `Agent-01` and sets a balance, per-transaction limit, daily limit, and approved merchants.
2. Agent performs a task and decides that it needs to make a payment.
3. Agent sends a request to `POST /payments` containing `agent_id`, `merchant_id`, `amount`, and a unique `request_id`.
4. Policy Server loads the agent and policy from SQLite.
5. Server rejects immediately if the agent status is `FROZEN`.
6. Server verifies the merchant is allowlisted.
7. Server checks the per-transaction amount.
8. Server calculates today's approved/settled spend and checks the daily limit.
9. *Optional*: Server checks transaction velocity and duplicate request IDs.
10. If all checks pass, the server calls the Payment Executor.
11. Payment Executor debits the simulated wallet (or sandbox provider) and records success.
12. Dashboard updates the transaction feed and remaining daily allowance.
13. If the owner presses **FREEZE**, the status changes to `FROZEN` and future requests are rejected independently of the agent.

---

## 8. Suggested Folder Structure

```text
agentpay-guard/
├── backend/
│   ├── main.py          # FastAPI Server
│   ├── policy.py        # Policy evaluation logic
│   ├── payments.py      # Payment Executor & Simulated Wallet
│   ├── database.py      # DB session initialization
│   └── models.py        # SQLAlchemy Models
├── agent/
│   ├── agent.py         # Autonomous agent runner / logic loop
│   └── scenarios.py     # Attack demo script / test scenarios
├── dashboard/
│   └── app.py           # Streamlit Web App (Owner Control)
├── tests/
│   └── test_policy.py   # Pytest suite for verification
├── data/
│   └── agentpay.db      # SQLite DB (local gitignored)
├── requirements.txt
└── README.md
```

---

## 9. Suggested Data Model

*   **`agents`**: `id`, `name`, `status` (ACTIVE/FROZEN), `balance`, `per_tx_limit`, `daily_limit`, `created_at`
*   **`merchants`**: `id`, `display_name`, `destination_reference`, `active`
*   **`agent_allowlist`**: `agent_id`, `merchant_id`
*   **`payment_requests`**: `request_id`, `agent_id`, `merchant_id`, `amount`, `status`, `reason`, `created_at`
*   **`transactions`**: `id`, `request_id`, `amount`, `balance_before`, `balance_after`, `settled_at`
*   **`audit_events`**: `id`, `actor`, `event_type`, `details`, `timestamp`

---

## 10. API Design

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| **POST** | `/payments` | Agent requests a payment. |
| **POST** | `/agents/{id}/freeze` | Owner freezes an agent. |
| **POST** | `/agents/{id}/unfreeze` | Owner re-enables an agent. |
| **PUT** | `/agents/{id}/policy` | Owner changes spend limits. |
| **POST** | `/agents/{id}/allowlist` | Owner adds an approved merchant. |
| **DELETE** | `/agents/{id}/allowlist/{merchant}` | Owner removes a merchant. |
| **GET** | `/agents/{id}` | Dashboard gets agent status and limits. |
| **GET** | `/agents/{id}/transactions` | Dashboard loads activity history. |

---

## 11. Security Rules

*   **Never** place payment-provider secrets in the agent code, prompt, browser, or repository.
*   **Separate** agent endpoints from owner/admin endpoints.
*   **Require** an owner/admin authentication mechanism for policy changes and freeze/unfreezes.
*   **Use** unique request IDs to prevent accidental/replayed duplicate payments.
*   **Perform** policy checks and payment execution server-side.
*   **Log** every approved and rejected request with a reason.
*   **Recheck** critical state immediately before executing delayed payments.

---

## 12. Build Plan

1.  **Core Policy**: Backend + simulated wallet. Done when: Valid payment succeeds; invalid amount fails.
2.  **Allowlist**: Merchant restrictions. Done when: Unknown merchant is blocked.
3.  **Kill Switch**: Freeze/unfreeze. Done when: Agent requests fail while frozen.
4.  **Dashboard**: Human controls + visibility. Done when: Limits/status/logs update from UI.
5.  **Attack Demo**: Automated scenarios. Done when: Overspend, unknown merchant, split-payments, and post-freeze actions all fail correctly.
6.  **Optional AI**: LLM chooses/requests actions. Done when: Agent can operate autonomously without manual per-payment approval.
