# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wallet is a full-stack personal finance tracker with:
- **Backend**: FastAPI + PostgreSQL + SQLAlchemy (async) + Alembic migrations
- **Frontend**: Vue 3 + TypeScript + PrimeVue + Pinia + Vite
- **Deployment**: Docker Compose with Nginx reverse proxy

## Development Commands

### Database
```bash
docker compose up db -d           # Start PostgreSQL
```

### Backend (from /backend)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head              # Run migrations
uvicorn app.main:app --reload     # Start dev server (http://localhost:8000)
```
API docs: http://localhost:8000/docs

### Frontend (from /frontend)
```bash
npm install
npm run dev      # Dev server with HMR (http://localhost:5173)
npm run build    # Production build
npm run preview  # Preview production build
```

### Production
```bash
docker compose up --build -d      # Build and start all services
```
App available at http://localhost:3000 (Nginx proxies /api/ to backend)

### Test Credentials
`admin@wallet.app` / `password`

## Architecture

### Backend Structure (app/)
- `api/` - FastAPI routers (auth, currencies, storage, transactions, analytics, etc.)
- `core/` - Config (pydantic-settings), database (async SQLAlchemy), security (JWT/bcrypt), dependencies (OAuth2)
- `models/` - SQLAlchemy ORM models with user_id scoping for multi-tenancy
- `schemas/` - Pydantic request/response schemas
- `services/` - Business logic (analytics with complex SQL aggregations)

Key patterns:
- All endpoints use async/await with AsyncSession
- JWT authentication via OAuth2PasswordBearer dependency
- All database records scoped to user_id (multi-tenant)

### Frontend Structure (src/)
- `api/` - Axios client with auto-inject JWT tokens and 401 redirect handling
- `stores/` - Pinia stores (auth with localStorage persistence, references for cached data)
- `views/` - Page components (Dashboard, Transactions, Expenses, Settings, etc.)
- `router/` - Vue Router with guest/protected route guards

Key patterns:
- Auth token stored in localStorage, injected via Axios interceptor
- Reference data (currencies, accounts, categories) cached in Pinia store
- PrimeVue Aura theme with dark mode support

### Database Models
User → Currency, StorageLocation, ExpenseCategory, IncomeSource
StorageLocation → StorageAccount (per currency)
StorageAccount → Transaction, BalanceSnapshot
Transaction links to ExpenseCategory (for expenses) or IncomeSource (for income)

### API Prefix
All backend routes use `/api` prefix. Frontend proxied through Nginx in production.