from celery import chain, shared_task


@shared_task
def compute_features(payload: dict | None = None):
    return payload or {"status": "features_computed"}


@shared_task
def generate_labels(payload: dict | None = None):
    return payload or {"status": "labels_generated"}


@shared_task
def train_models(payload: dict | None = None):
    return payload or {"status": "models_trained"}


@shared_task
def generate_rankings(payload: dict | None = None):
    return payload or {"status": "rankings_generated"}


@shared_task
def run_backtests(payload: dict | None = None):
    return payload or {"status": "backtests_completed"}


@shared_task
def monitor_drift(payload: dict | None = None):
    return payload or {"status": "drift_monitored"}


def build_daily_ml_chain(run_date: str):
    from project.apps.ingestion.tasks import download_bhavcopy

    return chain(
        download_bhavcopy.s(run_date),
        compute_features.s(),
        generate_labels.s(),
        train_models.s(),
        generate_rankings.s(),
        run_backtests.s(),
        monitor_drift.s(),
    )
