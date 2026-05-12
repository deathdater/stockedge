from celery import shared_task

from project.apps.core.pipeline import run_daily_ranking_pipeline


@shared_task
def generate_daily_rankings(run_date_iso: str | None = None, top_n: int = 25):
    return run_daily_ranking_pipeline(top_n=top_n)
