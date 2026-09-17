# Agora Bot

Telegram bot for **data automation**: scheduled reports, alerts, and structured exports.

Built as a practical example of integrating external APIs, processing data, and delivering results automatically via Telegram.

---

## What it does

- Pulls live data from external APIs
- Stores user state and history in a database
- Runs scheduled jobs (daily reports, recurring checks)
- Sends alerts when conditions are met
- Generates structured outputs (Excel tables, PDF reports, charts)
- Supports per-user timezones and persistent subscriptions

The current domain is market data, but the architecture is generic and can be adapted to almost any API-driven workflow (monitoring, reporting, notifications, etc.).

---

## Key capabilities

| Feature | Description |
|---------|-------------|
| **Scheduled delivery** | Daily price / chart / PDF reports at a user-defined time |
| **Conditional alerts** | Trigger notifications based on thresholds or indicator values |
| **Data processing** | Charts, comparison tables, portfolio-style aggregations |
| **Export formats** | Excel (`.xlsx`) and PDF reports |
| **State management** | FSM for multi-step commands + persistent storage |
| **Timezone support** | Jobs respect the user’s local time |

---

## Tech stack

- **Python 3.12**
- **aiogram 3** — async Telegram framework
- **SQLAlchemy 2 + aiosqlite** — async database layer
- **APScheduler** — background job scheduling
- **pandas / matplotlib** — data processing & visualization
- **Jinja2 + WeasyPrint** — PDF generation
- **Docker** — reproducible deployment

---

## Project structure
├── main.py              # Entry point
├── handlers.py          # Bot commands & conversation flow
├── jobs.py              # Scheduled task logic
├── scheduler.py         # APScheduler configuration
├── crud.py              # Database operations
├── models.py            # SQLAlchemy models
├── servicesnstuff.py    # Business logic, charts, reports
├── indicators.py        # Data transformation helpers
├── resilience.py        # Caching + retry utilities
├── templates/           # PDF report templates
├── Dockerfile
└── docker-compose.yml
text---

## Quick start (Docker)

1. Clone the repository
2. Create `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=sqlite+aiosqlite:////app/data/agora.db

Run:

Bashdocker compose up -d --build
The bot will start with all system dependencies (including PDF generation) already configured.

Example commands
text/price AAPL
/pricechart AAPL 3mo
/compare AAPL MSFT
/subscribe_price          → AAPL 09:30
/set_alert AAPL price above 200
/portfolio
/get_report AAPL

Why this project
This bot demonstrates practical skills useful for freelance automation work:

Working with external APIs and handling incomplete / unstable responses
Building reliable scheduled jobs
Generating documents (Excel + PDF) on demand
Managing user state and long-running background tasks
Packaging everything in Docker for easy deployment

The domain can be replaced with any other data source (CRM, analytics, monitoring systems, internal APIs, etc.) while keeping the same architecture.