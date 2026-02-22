# Wallet — Personal Finance Tracker

Full-stack app for tracking income, expenses, and balances across multiple storage accounts and currencies.

**Stack:** FastAPI + PostgreSQL + Vue 3 + PrimeVue

## Quick Start (Development)

### 1. Start PostgreSQL

```bash
docker compose up db -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python seed.py          # optional: import Excel data
uvicorn app.main:app --reload
```

API available at http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at http://localhost:5173

### Default credentials (from seed)

- Email: `admin@wallet.app`
- Password: `password`

## Production (Docker Compose)

```bash
docker compose up --build -d
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:3000/api/ (proxied through nginx)
