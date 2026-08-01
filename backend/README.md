# AgentPay Guard

> **Kill Switch & Policy-Enforced Payments for Autonomous AI Agents**

An independent payment-control layer that sits between an autonomous AI agent
and the payment system.  The agent can *request* payments, but never holds
credentials — every request is validated by a Policy Server that enforces
spend limits, merchant allowlists, and a human-operated freeze switch.

---

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (defaults work out of the box)
cp .env.example .env

# 4. Run the server
uvicorn app.main:app --reload
```

| What | Where |
|------|-------|
| Swagger UI | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| Default login | `admin@agentpay.dev` / `admin123` |

---

## Deploy to Render (Free Tier)

1. Push this repo to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Select **"Blueprint"** — the `render.yaml` auto-configures everything.
4. Set `SECRET_KEY` to a random value when prompted.

Or manually:

| Setting | Value |
|---------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log` |
| **Plan** | Free |

Also works on Railway, Fly.io, or any host that runs Python + uvicorn.

---

## Architecture

```
                        ┌─────────────────────┐
                        │   AI Agent          │
                        │  (no credentials)   │
                        └────────┬────────────┘
                                 │ POST /api/v1/payments
                                 ▼
                  ┌──────────────────────────┐
                  │     Policy Engine         │
                  │ 10 checks in order:       │
                  │ 1. Agent exists           │
                  │ 2. Agent ACTIVE           │
                  │ 3. Merchant exists        │
                  │ 4. Merchant ACTIVE        │
                  │ 5. Merchant allowlisted   │
                  │ 6. Per-tx limit           │
                  │ 7. Daily limit            │
                  │ 8. Rate limit             │
                  │ 9. No duplicate request   │
                  │10. Wallet balance         │
                  └────────┬─────────────────┘
                           │ APPROVED
                           ▼
                  ┌──────────────────────────┐
                  │   Payment Executor        │
                  │ • Debit simulated wallet  │
                  │ • Create transaction      │
                  │ • Write audit log         │
                  └──────────────────────────┘
```

### Freeze Switch

```
POST /api/v1/agents/{id}/freeze   →  AGENT FROZEN
                                    →  Every payment BLOCKED immediately
```

---

## API Endpoints

### Authentication
`POST   /api/v1/auth/register` – Create account  
`POST   /api/v1/auth/login` – Get JWT token  
`GET    /api/v1/auth/me` – Current user profile

### Agents
`POST   /api/v1/agents` – Create agent  
`GET    /api/v1/agents` – List agents  
`GET    /api/v1/agents/{id}` – Get agent  
`PUT    /api/v1/agents/{id}` – Update agent  
`DELETE /api/v1/agents/{id}` – Delete agent  
`POST   /api/v1/agents/{id}/freeze` – **Freeze (kill switch)**  
`POST   /api/v1/agents/{id}/unfreeze` – Unfreeze  
`PUT    /api/v1/agents/{id}/policy` – Update spending policy

### Merchants
`POST   /api/v1/merchants` – Create merchant  
`GET    /api/v1/merchants` – List merchants  
`DELETE /api/v1/merchants/{id}` – Delete merchant

### Allowlist
`GET    /api/v1/agents/{id}/allowlist` – List allowed merchants  
`POST   /api/v1/agents/{id}/allowlist` – Add merchant to allowlist  
`DELETE /api/v1/agents/{id}/allowlist/{merchant_id}` – Remove

### Payments
`POST   /api/v1/payments` – Agent requests payment

### Dashboard
`GET    /api/v1/dashboard/summary` – KPIs (agents, spending, counts)  
`GET    /api/v1/dashboard/activity` – Recent payment activity  
`GET    /api/v1/dashboard/audit` – Audit log

### AI (Optional)
`POST   /api/v1/ai/explain-blocked` – Explain why payment was blocked  
`POST   /api/v1/ai/explain-policy` – Explain spending policy  
`GET    /api/v1/ai/summarize-audit` – Summarize audit log

### System
`GET    /health` – Liveness check

---

## Configuration

All settings are in `app/core/config.py` and can be overridden via environment
variables or a `.env` file.  See `.env.example` for the full list.

Key settings:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **change for production** |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/agentpay.db` | Database connection |
| `GROQ_API_KEY` | (empty) | Enable AI explanations via Groq |
| `GEMINI_API_KEY` | (empty) | Enable AI explanations via Gemini |

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

88 tests covering: authentication, CRUD, freeze/unfreeze, policy engine
(all 10 checks), payment executor, wallet, rate limiting, duplicate detection,
daily limits, audit logs, dashboard, and AI fallback.

---

## Project Structure

```
agentpay-guard/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── api/                     # Routers, deps, schemas
│   │   ├── endpoints/           # auth, agents, merchants, allowlist,
│   │   │                       # payments, dashboard, ai
│   │   ├── router.py            # Central router (/api/v1)
│   │   ├── deps.py              # Session + auth dependencies
│   │   └── exceptions.py        # Global error handlers
│   ├── core/
│   │   ├── config.py            # Pydantic BaseSettings
│   │   ├── constants.py         # Enums & rejection reasons
│   │   └── logging.py           # Structured / coloured logging
│   ├── db/
│   │   ├── session.py           # Async engine + session factory
│   │   └── init_db.py           # Table creation + owner seed
│   ├── models/                  # SQLAlchemy ORM models
│   └── services/                # Business logic
│       ├── policy_engine.py     # 10-check payment gate
│       ├── payment_executor.py  # Simulated wallet
│       ├── dashboard_service.py # Read-only aggregations
│       ├── ai_service.py        # Unified AI (Groq / Gemini)
│       └── ai/                  # Provider implementations
├── tests/                       # 88 pytest tests
├── alembic/                     # DB migrations (optional)
├── data/                        # SQLite DB (runtime)
├── requirements.txt             # Dependencies
├── render.yaml                  # Render Blueprint
├── Procfile                     # Heroku / Railway
├── pytest.ini                   # asyncio_mode = auto
├── .env.example                 # Environment template
└── README.md                    # This file
```

---

## Technology

| Layer | Choice | Why |
|-------|--------|-----|
| API | FastAPI | Async, auto OpenAPI docs, Python-native |
| Database | SQLite + aiosqlite | Zero setup, works everywhere |
| ORM | SQLAlchemy 2.0 | Full async support |
| Auth | JWT (python-jose) + bcrypt | Stateless, industry standard |
| Config | Pydantic Settings | Type-safe env vars |
| AI | Groq / Gemini | Explanations & summaries (optional) |

---

## License

MIT — built for hackathon demonstration purposes.
