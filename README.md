# FinPilot — AI-Powered Personal Finance Platform

> Your AI co-pilot for smarter finances.

[![CI/CD](https://github.com/yourusername/finpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/finpilot/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Django 5.1](https://img.shields.io/badge/django-5.1-green.svg)](https://djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[Live Demo →](https://finpilot.railway.app)** | **[API Docs →](https://finpilot.railway.app/api/docs/)**

---

## Overview

FinPilot is a production-ready, AI-powered personal finance management platform built with Django, Django REST Framework, and Claude AI. It transforms raw transaction data into actionable financial intelligence through an intuitive, modern UI.

---

## Features

### Core Finance
- [x] Multi-account tracking (bank, cash, credit card, savings)
- [x] Income & expense transaction management with full CRUD
- [x] Category system with icons and colour coding (13 defaults + custom)
- [x] Monthly budget limits per category with alert thresholds
- [x] Savings goals with deadline tracking and monthly contribution calculator
- [x] EMI & liability tracker with amortisation formula (handles compound interest)
- [x] Recurring transaction rules (daily / weekly / monthly / yearly)

### Analytics & Reporting
- [x] Financial Health Score (0–100) from savings rate, expense ratio, EMI burden
- [x] 6-month and 12-month cash flow trend charts (Chart.js)
- [x] Spending breakdown by category (donut chart)
- [x] Budget utilisation progress bars with over-budget alerts
- [x] End-of-month spending forecasts using 3-month rolling averages
- [x] Anomaly detection — flags transactions 2σ above category average

### AI Features (Claude API)
- [x] Weekly AI financial insights — personalised analysis of spending patterns
- [x] Natural language transaction entry — "Spent ₹450 on Zomato yesterday"
- [x] Statistical anomaly detection with human-readable alerts
- [x] Rule-based insight fallback when API key not configured

### Technical
- [x] Full REST API with JWT authentication (DRF + SimpleJWT)
- [x] OpenAPI / Swagger documentation at `/api/docs/`
- [x] Per-user data isolation with UUID primary keys
- [x] DecimalField for all monetary values (no float precision errors)
- [x] Database indexes on high-frequency query fields
- [x] Service layer architecture (business logic out of views)
- [x] 40+ tests (models, services, views, API endpoints)
- [x] Docker + docker-compose for local development
- [x] GitHub Actions CI pipeline

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1, Django REST Framework 3.15 |
| Auth | JWT (SimpleJWT), Django sessions |
| Database | PostgreSQL (production), SQLite (dev) |
| AI | Anthropic Claude API (claude-sonnet-4) |
| Frontend | Django Templates, Chart.js, Vanilla JS |
| Fonts | Plus Jakarta Sans, DM Sans, JetBrains Mono |
| Deployment | Railway / Heroku, Docker, Gunicorn, WhiteNoise |
| CI/CD | GitHub Actions |

---

## Architecture

```
finpilot/
├── finpilot/           # Django project config
│   ├── settings.py     # Environment-based, split dev/prod
│   └── urls.py         # Root URL routing
├── fin_manager/        # Core application
│   ├── models.py       # 9 models: UserProfile, Account, Category,
│   │                   #   Transaction, Budget, Liability,
│   │                   #   SavingsGoal, RecurringRule, AIInsight
│   ├── services.py     # Service layer: Dashboard, Insight,
│   │                   #   Prediction, Transaction services
│   ├── views.py        # Thin template views
│   ├── api_views.py    # DRF ViewSets + API views
│   ├── serializers.py  # DRF serializers with validation
│   ├── filters.py      # django-filter Transaction filters
│   ├── forms.py        # Django ModelForms
│   └── tests.py        # 40+ unit + integration tests
├── templates/          # Django HTML templates
├── static/             # CSS design system + JS
│   ├── css/main.css    # Complete design system (1000+ lines)
│   └── js/main.js      # Modal, sidebar, tab interactions
└── docker-compose.yml  # Local dev: app + postgres + redis
```

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/register/` | POST | Create account |
| `/api/auth/token/` | POST | Obtain JWT tokens |
| `/api/dashboard/` | GET | Full dashboard data |
| `/api/transactions/` | GET/POST | List, filter, create |
| `/api/transactions/{id}/` | GET/PUT/DELETE | Detail CRUD |
| `/api/budgets/current_month/` | GET | This month's budgets |
| `/api/goals/{id}/add_funds/` | POST | Add to savings goal |
| `/api/ai/insights/` | GET | AI-generated insights |
| `/api/ai/nlp-transaction/` | POST | Natural language entry |
| `/api/ai/predictions/` | GET | Spending forecasts |
| `/api/reports/summary/` | GET | Historical summary |

---

## Local Setup

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/yourusername/finpilot.git
cd finpilot
cp .env.example .env          # Add your ANTHROPIC_API_KEY
docker-compose up --build
# App at http://localhost:8000
```

### Option 2 — Manual

```bash
git clone https://github.com/yourusername/finpilot.git
cd finpilot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Edit: SECRET_KEY, DATABASE_URL, ANTHROPIC_API_KEY
python manage.py migrate
python manage.py runserver
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key — generate with `django-admin` |
| `DEBUG` | No | `True` for dev, `False` for prod |
| `DATABASE_URL` | No | Defaults to SQLite. Use postgres:// for prod |
| `ANTHROPIC_API_KEY` | No | For AI features. App works without it (rule-based fallback) |
| `SENTRY_DSN` | No | Error tracking |

---

## Running Tests

```bash
python manage.py test fin_manager --verbosity=2
```

---

## Deployment (Railway)

1. Push repo to GitHub
2. Create new project on [Railway](https://railway.app)
3. Add PostgreSQL service
4. Set environment variables (copy from `.env.example`)
5. Deploy — the `Procfile` handles migrations + gunicorn automatically

---

## AI Features

### How insights work
Every week (or on demand), FinPilot sends a summary of your last 90 days of categorised transactions to the Claude API. The model returns 3 structured insights (trend / anomaly / saving opportunity) which are cached in the database. The app displays them as insight cards on the dashboard and AI Insights page.

If `ANTHROPIC_API_KEY` is not set, the app falls back to rule-based insights (savings rate below 20%, budget overspend alerts, etc.).

### Natural language transaction entry
Type "Spent ₹450 on Swiggy yesterday" in the AI Entry tab. Claude extracts `amount`, `date`, `transaction_type`, and `category_hint`, then creates the transaction automatically. The transaction is flagged with an AI badge.

---

## Resume Impact

> *Built FinPilot, an AI-powered personal finance platform using Django REST Framework, PostgreSQL, and Claude AI — featuring multi-account tracking, budget analytics, Financial Health Score, natural language transaction entry, and spending anomaly detection. Deployed with Docker, GitHub Actions CI, and JWT-authenticated REST API with OpenAPI documentation.*

---

## Roadmap

- [ ] CSV/Excel bank statement import with auto-categorisation
- [ ] Monthly PDF financial report (email delivery)
- [ ] WhatsApp bot for transaction logging
- [ ] Investment portfolio tracking (NSE/BSE integration)
- [ ] Family/shared budget accounts
- [ ] Debt payoff planner (avalanche vs snowball)