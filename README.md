# StockEdge

StockEdge is a Django + Celery based quant research and ranking pipeline for daily equity data. It ingests bhavcopy files, validates and stores candles, computes leakage-safe features, generates horizon labels, trains model families, ranks symbols, and supports backtesting/drift monitoring workflows.

## Quick Start (Docker)

1. Copy env template:
   ```bash
   cp .env.example .env
   ```
2. Build and start all services:
   ```bash
   docker compose up --build
   ```
3. Run tests in container:
   ```bash
   docker compose run --rm web pytest -q
   ```
4. Open app on `http://localhost:8000`.

## Services and Persistence Layers

`docker-compose.yml` provisions:

- **web**: Django/Gunicorn HTTP service.
- **worker**: Celery worker for ingestion/model/backtest tasks.
- **beat**: Celery scheduler (periodic workflows).
- **db**: PostgreSQL 16 (persistent volume `postgres_data`).
- **redis**: Redis 7 broker/result backend with AOF persistence (`redis_data`).

Persistent volumes:

- `postgres_data` for relational data
- `redis_data` for broker durability
- `web_data` for app-local persistent artifacts

## Local (non-docker) setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
pytest -q
python manage.py runserver
```

## Useful Commands

- `make test` – run pytest suite.
- `docker compose logs -f web worker` – inspect runtime logs.
- `docker compose down -v` – stop and remove containers + volumes.

## Test Coverage Added

The `tests/` suite includes deterministic fixtures and coverage for:

- ingestion validation and idempotency-adjacent parsing constraints,
- leakage-safe rolling feature calculations,
- horizon-based label correctness,
- Celery pipeline chain ordering,
- walk-forward split temporal integrity,
- backtesting constraints (fees/slippage/exposure + delayed fill).

See `docs/ARCHITECTURE.md` for a deep walkthrough.
