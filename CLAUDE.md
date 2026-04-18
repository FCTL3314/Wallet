# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wallet is a full-stack personal finance tracker with:

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy (async) + Alembic migrations
- **Frontend**: Vue 3 + TypeScript + PrimeVue + Pinia + Vite
- **Deployment**: Docker Compose with Nginx reverse proxy (images published to `ghcr.io`)

## Production Deployment

The production server contains **only two files** in `/opt/wallet/`:

- `docker-compose.yml` — pulled from this repo's `docker/prod/docker-compose.yml`
- `.env` — secrets and env-specific config, managed manually on the server

Images are pulled from `ghcr.io/${OWNER}/wallet-{backend,frontend,report-service,backup}:${IMAGE_TAG:-latest}`.
There is **no source code** on the server — changes require rebuilding and pushing images via CI.

**Critical rule**: a variable in `.env` is NOT automatically injected into a container.
Every env var must be explicitly listed in the `environment:` section of `docker-compose.yml`.
If you add a new `Settings` field in `app/core/config.py` that needs to be configurable in production,
you must also add `VAR_NAME: ${VAR_NAME:-default}` to the `backend` service in `docker/prod/docker-compose.yml`.

Restart a single service on the server:

```bash
docker compose -f /opt/wallet/docker-compose.yml up -d --no-deps backend
```

## Code Standards

- **Language**: All code, comments, error messages, and documentation in English
- **Best practices**: Use modular architecture, proven patterns, and clean separation of concerns
- **Error handling**: Use standardized error codes (see `app/core/exceptions.py`)

## Python Code Standards

- Use `X | None` instead of `Optional[X]`; use `X | Y` instead of `Union[X, Y]`
- Use built-in generic types: `list[x]`, `dict[k, v]`, `tuple[x, y]` (not `typing.List`, `typing.Dict`, etc.)
- Never use Python builtin names as identifiers: `type`, `id`, `list`, `dict`, `filter`, `input`, `format`, etc.
- All imports must be at the top of the file; never import inside functions (except to break circular imports)
- Use `get_or_404()` from `app/core/db_helpers.py` for all user-scoped resource lookups

## Development Commands

### Docker (recommended)

```bash
make dev          # Start dev environment (frontend :5173, backend :8000)
make dev-build    # Rebuild and start
make dev-down     # Stop dev environment
make db           # Start only database
make logs         # Follow dev logs
```

### Production

```bash
make prod         # Start production (app at :3000)
make prod-build   # Rebuild and start
make prod-down    # Stop production
```

### Tests

```bash
make test
```

### Local Development (without Docker)

**Database:**

```bash
make db                           # Start PostgreSQL in Docker
```

**Backend (from /backend):**

```bash
uv sync
uv run alembic upgrade head              # Run migrations
uv run uvicorn app.main:app --reload     # Start dev server (http://localhost:8000)
```

API docs: http://localhost:8000/docs

**Frontend (from /frontend):**

```bash
npm install
npm run dev      # Dev server with HMR (http://localhost:5173)
npm run build    # Production build
npm run preview  # Preview production build
```

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

## Frontend Design System

Design reference: https://github.com/FCTL3314/HealthNutrition-Frontend

### Core Concept: Everything is a Card ("плашка")

**The one rule**: nothing floats on the bare background. Every piece of UI lives inside a card.

This comes directly from the reference's `ComponentWrapper.vue` pattern:

- White background (`#ffffff`)
- Border radius: `var(--radius-card)` = `24px` (reference uses `2rem`)
- Subtle border + drop shadow
- Consistent gap between cards: `var(--gap-section)` = `24px` (reference: `$between-components-indentation: 1.5rem`)

**What counts as a card:** `BaseCard` / `.card` class. Use it for everything:

- Navigation header → floating card with margin from edges (`top: 16px; left/right: 24px`)
- Filter bars / toolbars → inside a `<BaseCard>`
- Data tables → `BaseDataTable` already wraps in `BaseCard`
- Stat cards → `.stat-card` is its own surface
- Modals → `.modal` is a card

**Page layout pattern:**

```
[light-gray background rgb(245,244,251)]
  [floating header card — fixed, margin 16px top / 24px sides]

  [page-title — tiny muted label, not a hero heading]
  [div.page-sections — flex-column, gap: 24px]
    [BaseCard]   ← filters
    [stats-grid] ← group of stat cards
    [BaseDataTable] ← already a card
```

### Color Palette (from reference)

| Token                  | Value              | Meaning                                         |
|------------------------|--------------------|-------------------------------------------------|
| `--bg-base`            | `rgb(245,244,251)` | Page background (light lavender from reference) |
| `--color-accent`       | `#5585c5`          | Pastel cornflower blue                          |
| `--color-accent-light` | `#78a8e0`          | Light pastel blue                               |
| `--color-income`       | `#4aaa80`          | Pastel mint green                               |
| `--color-expense`      | `#d46878`          | Pastel rose red                                 |
| `--color-warning`      | `#e0b84a`          | Pastel amber                                    |
| `--color-cyan`         | `#4cbecb`          | Pastel teal                                     |
| `--card-bg`            | `#ffffff`          | Card surface                                    |

**Variable naming rule**: variable names must match their actual color/purpose. Never `--color-gold` for yellow, never
`--color-coral` for unused pinks.

### Avoid

- Full-width edge-to-edge bars (header, toolbars) — they must be cards with margin/padding
- Floating content directly on `--bg-base` — always wrap in a card first
- Dark theme colors (rgba white overlays, dark backgrounds in main content)
- Inventing new accent colors — use only the 4 semantic colors above + cyan

## Frontend Standards (Vue 3 + TypeScript)

### File Structure

- `src/composables/` — reusable composable functions (`useAsync`, `useCrudSection`, etc.)
- `src/types/` — shared TypeScript interfaces and types (not inline in files)
- `src/components/Base*.vue` — reusable base components (`BaseDialog`, `BaseTable`, etc.)

### Composition API Rules

- Always use `<script setup lang="ts">`
- Use `storeToRefs()` when destructuring state from Pinia stores (preserves reactivity)
- Use `computed()` (not methods or inline expressions) for all derived/transformed data
- Use `useTemplateRef<T>('name')` instead of `ref<T | null>(null)` for DOM refs
- Use `defineModel()` for two-way binding in child components

### Type Safety

- No `any` types — define interfaces in `src/types/` and import them
- Router meta must use the `RouteMeta` interface (augment in `src/router/index.ts`)
- API filter params must be typed interfaces, not plain objects
- Use `as const` for enum-like string literals

### Data Fetching Pattern (required for all views)

Use the `useAsync` composable from `src/composables/useAsync.ts`:

```typescript
const {data, loading, error, execute} = useAsync(() => api.list())
```

- Exposes: `data: Ref<T | null>`, `loading: Ref<boolean>`, `error: Ref<string | null>`, `execute()`
- `watch()` reactive params → call `execute()` to reload
- `finally` block always resets `loading`

### Component Naming

- Base/reusable: `BaseDialog.vue`, `BaseTable.vue`, `BaseConfirmButton.vue`
- Page-scoped slots only: `TheNavbar.vue`, `TheSidebar.vue`
- Feature-scoped: `TransactionForm.vue`, `CategoryRow.vue`

### Stores

- Setup stores (`defineStore('id', () => {})`) preferred over Options stores
- Use `storeToRefs()` in components: `const { token } = storeToRefs(authStore)`
- Lookup helpers (e.g. `currencyById`) use `Map` not linear `find()` for O(1) access

### Component-First Interactive Patterns

- Never duplicate interactive patterns inline — always encapsulate in a shared component
- Edit + Delete pair → always use `EditDeleteActions.vue` (handles pending state + animations)
- Any pattern used in 2+ places must become a base/feature component

### Avoid

- `confirm()` for deletion — use a modal or inline confirmation
- `refs.fetchAll()` after every CRUD op — update local state or fetch only changed resource
- Inline `reduce()` / `find()` in template expressions — use `computed()`
- Hardcoded locale strings (currency symbols, language codes)