# Sales CRM

A self-contained Sales CRM built with **FastAPI + SQLite** (backend) and **vanilla HTML/CSS/JS** (frontend).

## Features

| Feature | Details |
|---|---|
| **Leads** | Create, score, qualify, and convert leads into contacts + projects with one click |
| **Contacts** | Full contact management linked to accounts and projects; searchable by email |
| **Accounts** | Company accounts with domain matching used for auto-mapping email threads |
| **Projects** | Deals linked to accounts/leads; auto-creates a sales cycle on creation |
| **Email Ingestion** | Paste/POST an email thread – the system auto-maps the sender to a Contact and links to an active Project by email/domain; creates a Lead if no match found |
| **Stakeholder Profiling** | Auto-identify stakeholders from project contacts + email participants; enrich profiles via LinkedIn scraping |
| **LinkedIn Scraper** | Works in **mock mode** by default (realistic synthetic data); set `RAPIDAPI_KEY` env var to enable real LinkedIn lookups via RapidAPI |
| **Sales Cycle** | 8-stage pipeline (Prospecting → Closed Won/Lost); advance stages, log activities, view pipeline Kanban |

## Quick Start

```bash
chmod +x start.sh
./start.sh
```

Then open **http://localhost:8000**

API docs (Swagger UI): **http://localhost:8000/docs**

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./sales_crm.db` | Database connection string |
| `RAPIDAPI_KEY` | _(empty)_ | Enable real LinkedIn scraping via RapidAPI |

## Architecture

```
sales-crm/
├── backend/
│   ├── main.py                   # FastAPI app, CORS, static file serving
│   ├── database.py               # SQLAlchemy engine + session
│   ├── models.py                 # ORM models: Account, Contact, Lead, Project,
│   │                             #   Stakeholder, SalesCycle, Activity, EmailThread
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── routers/
│   │   ├── accounts.py           # CRUD /api/v1/accounts
│   │   ├── contacts.py           # CRUD + email search
│   │   ├── leads.py              # CRUD + /convert endpoint
│   │   ├── projects.py           # CRUD + auto sales-cycle creation
│   │   ├── stakeholders.py       # CRUD + LinkedIn scan + auto-identify
│   │   ├── emails.py             # Ingest raw/parsed emails, auto-map
│   │   └── sales_cycle.py        # Stage advance, activity log, pipeline summary
│   └── services/
│       ├── email_parser.py       # RFC-2822 parsing, email extraction, auto-mapping
│       ├── linkedin_scraper.py   # Mock + RapidAPI LinkedIn profile fetcher
│       └── sales_cycle_manager.py# Stage transitions, probability, activity logging
└── frontend/
    ├── index.html                # SPA shell
    ├── style.css                 # Dark-mode design system
    └── app.js                    # Vanilla JS router + page renderers
```

## Sales Cycle Stages & Default Probabilities

| Stage | Probability |
|---|---|
| Prospecting | 5% |
| Qualification | 15% |
| Needs Analysis | 25% |
| Value Proposition | 40% |
| Proposal | 60% |
| Negotiation | 80% |
| Closed Won | 100% |
| Closed Lost | 0% |

## Email Auto-Mapping Logic

1. Extract `from_email` from the thread.
2. Look up `from_email` in the **Contacts** table.
3. If found, link thread to contact and find their active project.
4. If not found, try matching the email **domain** against **Account.domain**.
5. If still no match, auto-create a **Lead** from the sender.

## LinkedIn Scraping

- **Mock mode** (default): deterministic synthetic profiles generated from the URL slug – useful for demos and testing.
- **RapidAPI mode**: set `RAPIDAPI_KEY` to use the *Fresh LinkedIn Profile Data* API on RapidAPI for real profiles.
