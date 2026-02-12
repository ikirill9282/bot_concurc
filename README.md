# Telegram Giveaway Referral Bot

Production-ready Telegram giveaway bot built with `aiogram v3`, `PostgreSQL 16`, `SQLAlchemy async`, `Alembic`, and Docker webhook deployment behind nginx TLS.

## Features

- `/start` and `/start <ref_code>` flow with fraud checks.
- Channel subscription verification with Telegram `getChatMember`.
- DB-backed per-user rate limit for subscription checks (1 check / 5 seconds).
- Transactional and idempotent referral confirmation.
- Permanent participant state when both conditions are met:
  - `is_subscribed = true`
  - `referrals_confirmed >= 1`
- Admin commands:
  - `/stats`
  - `/export`
  - `/broadcast <message>`
- Structured JSON logging.
- Health endpoints:
  - `GET /healthz`
  - `GET /readyz`

## Architecture

- `bot`: aiogram bot with long polling (no webhook needed)
- `db`: PostgreSQL database
- Works **without Docker** - lightweight deployment (~300 MB vs 2-3 GB)

## Prerequisites

- Python 3.11+
- PostgreSQL
- Telegram bot token from BotFather
- **No domain needed** - uses long polling mode

## Quick Start (Recommended - No Docker)

### Automatic Installation

```bash
# On your server
cd ~/projects/colchuga_bot
bash scripts/install.sh
```

### Manual Installation

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for detailed step-by-step guide or **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** for quick reference.

**Minimal setup:**
1. Install Python 3.11+ and PostgreSQL
2. Create virtual environment: `python3 -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Configure `.env` with `SKIP_WEBHOOK_SETUP=true`
5. Run migrations: `alembic upgrade head`
6. Start bot: `python -m app.main`

## Docker Deployment (Optional)

If you prefer Docker, see the old deployment guide in `DEPLOYMENT.md` (Docker section).

```bash
docker compose up --build -d
```

## Commands

- User:
  - `/start`
  - `Check Again` button for subscription verification.
- Admin-only (IDs from `ADMIN_IDS`):
  - `/stats`
  - `/export`
  - `/broadcast Your message`

## Database migrations

Apply migrations manually:

```bash
source venv/bin/activate  # if using virtual environment
alembic upgrade head
```

## Local tests

```bash
pytest
```

## Deployment

**Recommended: Simple deployment without Docker** (~300 MB vs 2-3 GB)

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete step-by-step guide (no Docker)
- **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** - Quick reference guide

**Automated installation:**
```bash
bash scripts/install.sh
```

**Key advantages:**
- ✅ No Docker needed - saves ~2-3 GB disk space
- ✅ Simple systemd service management
- ✅ Works without domain (long polling mode)
- ✅ Easy debugging with journalctl logs

## Security notes

- Secrets are provided only through environment variables.
- Secrets are not logged.
- Webhook endpoint validates Telegram secret token header.
- Referral logic uses Telegram numeric IDs only.
