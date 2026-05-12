# StockEdge Architecture Walkthrough

## 1) End-to-end pipeline

The intended ML pipeline chain is:

1. `download_bhavcopy`
2. `compute_features`
3. `generate_labels`
4. `train_models`
5. `generate_rankings`
6. `run_backtests`
7. `monitor_drift`

`project/apps/core/tasks.py` defines chain-friendly task wrappers and `build_daily_ml_chain(run_date)` to construct this exact sequence.

## 2) Application module walkthrough

### Ingestion (`project/apps/ingestion`)

- `validators.py`: `DataValidator.parse_row` enforces required fields and OHLCV consistency checks.
- `tasks.py`: handles ZIP download, checksum verification, CSV extraction, per-row validation, and `DailyCandle.update_or_create` for idempotent persistence.
- `metrics.py`: lightweight increment hooks for observability.

### Market data (`project/apps/market_data`)

- `models.py`: canonical daily candle storage (`symbol`, `date`, OHLC, volume).

### Features (`project/apps/features`)

- `contracts.py`: typed data carriers (`FeatureInputRow`, `FeatureOutputRow`).
- `services.py`: `compute_leakage_safe_rolling_features` computes lag/rolling stats from historical-only context to avoid lookahead leakage.

### Labels (`project/apps/labels`)

- `contracts.py`: typed label records.
- `services.py`: `build_future_return_labels` computes future return and direction by configured horizon.

### ML models (`project/apps/ml_models`)

- `services.py`: `make_walk_forward_folds` creates chronological folds (train then future validation windows), and training family stub for model groups.

### Ensemble/Ranking (`project/apps/ensemble`, `project/apps/rankings`, `project/apps/core/pipeline.py`)

- Signal-level score composition via weighted ensemble strategy.
- Pipeline computes rank candidates from daily candles and persists top-N rankings.

### Backtesting (`project/apps/backtesting`)

- `run_vectorbt_backtest` applies delay, slippage, fees, and exposure config into `vectorbt.Portfolio.from_signals`.

### Monitoring (`project/apps/monitoring`)

- Placeholder service layer for post-train and post-backtest drift checks.

### API (`project/apps/api`)

- Django views/templates + FastAPI integration point (`fastapi_app.py`).

## 3) Runtime and deployment model

### Containerized runtime

- `Dockerfile`: builds Python runtime, installs requirements, and starts via `scripts/entrypoint.sh`.
- `entrypoint.sh`: applies migrations before launching process.
- `docker-compose.yml`: composes web, worker, beat, PostgreSQL, and Redis.

### Persistence and state

- PostgreSQL volume stores application data.
- Redis volume stores broker AOF for durable queue state.
- Optional app data volume for exports/artifacts.

## 4) Settings and environment controls

`project/settings/base.py` reads:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `DATABASE_URL` (sqlite or postgres URL parsing)
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

By default (without `DATABASE_URL`) it falls back to local sqlite for lightweight development.

## 5) Testing strategy

Deterministic tests live under `tests/` and cover:

- validation rules,
- leakage-safe feature engineering,
- label correctness by horizon,
- Celery task-chain order,
- walk-forward split integrity,
- backtest config pass-through.

Tooling:

- `pytest.ini` for test discovery.
- `Makefile` target `test`.
- GitHub Actions workflow `.github/workflows/tests.yml`.

## 6) Operational checklist

- Keep migrations forward-only and committed with model changes.
- Ensure Celery broker/backends are reachable before worker start.
- Monitor ingestion failures and checksum mismatches.
- Validate drift metrics before promoting model/ranking changes.
