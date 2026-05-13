"""Views for StockEdge dashboard, pipeline control, and prediction display."""

from datetime import date, datetime, timedelta

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from project.apps.features.models import DailyFeature
from project.apps.ingestion.models import IngestionRun
from project.apps.labels.models import PredictionLabel
from project.apps.market_data.models import DailyCandle
from project.apps.ml_models.models import ModelRun
from project.apps.rankings.models import DailyRanking


@require_http_methods(["GET", "POST"])
def dashboard(request: HttpRequest) -> HttpResponse:
    # Find the latest date with ingested candle data
    latest_candle_date = DailyCandle.objects.order_by("-date").values_list("date", flat=True).first()
    default_date = latest_candle_date or date.today()

    selected_date = request.GET.get("date", "")
    if selected_date:
        try:
            run_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            run_date = default_date
    else:
        run_date = default_date

    rankings = DailyRanking.objects.filter(date=run_date).order_by("rank")[:25]

    # Pipeline status summary
    ingestion_stats = IngestionRun.objects.filter(source="bhavcopy_daily")
    features_count = DailyFeature.objects.filter(date=run_date).count()
    labels_count = PredictionLabel.objects.filter(date=run_date).count()
    candles_count = DailyCandle.objects.filter(date=run_date).count()
    model_runs = ModelRun.objects.order_by("-created_at")[:4]

    # Available dates for the date picker
    date_range = DailyCandle.objects.order_by("date").values_list("date", flat=True)
    min_date = date_range.first() if date_range.exists() else None
    max_date = date_range.last() if date_range.exists() else None

    # Recent dates with rankings already computed
    ranked_dates = list(
        DailyRanking.objects.order_by("-date").values_list("date", flat=True).distinct()[:10]
    )

    context = {
        "rankings": rankings,
        "run_date": run_date,
        "selected_date": run_date.isoformat(),
        "latest_date": default_date,
        "features_count": features_count,
        "labels_count": labels_count,
        "candles_count": candles_count,
        "model_runs": model_runs,
        "min_date": min_date,
        "max_date": max_date,
        "ranked_dates": ranked_dates,
        "ingestion_success": ingestion_stats.filter(status="success").count(),
        "ingestion_total": ingestion_stats.count(),
        "total_candles": DailyCandle.objects.count(),
        "total_symbols": DailyCandle.objects.values("symbol").distinct().count(),
    }
    return render(request, "api/dashboard.html", context)


@require_POST
def trigger_pipeline(request: HttpRequest) -> HttpResponse:
    """Trigger the full ML pipeline for a specific date via Celery (async, idempotent)."""
    run_date = request.POST.get("run_date", date.today().isoformat())

    from project.apps.core.tasks import build_daily_ml_chain

    chain = build_daily_ml_chain(run_date)
    result = chain.apply_async()

    return JsonResponse({
        "status": "dispatched",
        "task_id": result.id,
        "run_date": run_date,
        "message": f"Pipeline dispatched for {run_date}. Tasks are idempotent — no duplicate work.",
    })


@require_POST
def trigger_ranking_only(request: HttpRequest) -> HttpResponse:
    """Run ranking pipeline synchronously for a specific date."""
    run_date_str = request.POST.get("run_date", date.today().isoformat())
    try:
        run_date = datetime.strptime(run_date_str, "%Y-%m-%d").date()
    except ValueError:
        run_date = date.today()

    from project.apps.core.pipeline import run_daily_ranking_pipeline

    result = run_daily_ranking_pipeline(run_date=run_date)
    return redirect(f"/ui/?date={run_date.isoformat()}")


@require_GET
def prediction_page(request: HttpRequest) -> HttpResponse:
    symbol = request.GET.get("symbol", "").upper().strip()
    prediction = None
    features = None
    labels = None
    price_history = None

    if symbol:
        # Get latest ranking
        prediction = DailyRanking.objects.filter(symbol=symbol).order_by("-date").first()

        if prediction:
            # Get features for the prediction date
            features = DailyFeature.objects.filter(
                symbol=symbol,
                date=prediction.date,
                feature_set="baseline_v1",
            ).first()

            # Get recent labels
            labels = list(
                PredictionLabel.objects.filter(symbol=symbol)
                .order_by("-date")[:10]
                .values("date", "future_return", "direction", "horizon_days")
            )

            # Get price history (last 30 days)
            price_history = list(
                DailyCandle.objects.filter(symbol=symbol)
                .order_by("-date")[:30]
                .values("date", "open", "high", "low", "close", "volume")
            )

    # All-time ranking dates for quick navigation
    recent_dates = list(
        DailyRanking.objects.order_by("-date").values_list("date", flat=True).distinct()[:10]
    )

    # Top symbols for autocomplete
    top_symbols = list(
        DailyRanking.objects.order_by("-date", "rank")
        .values_list("symbol", flat=True)
        .distinct()[:50]
    )

    context = {
        "symbol": symbol,
        "prediction": prediction,
        "features": features,
        "labels": labels,
        "price_history": price_history,
        "recent_dates": recent_dates,
        "top_symbols": top_symbols,
    }
    return render(request, "api/prediction.html", context)


@require_GET
def pipeline_status(request: HttpRequest) -> JsonResponse:
    """API endpoint for checking pipeline status (used by AJAX polling)."""
    run_date_str = request.GET.get("date", date.today().isoformat())
    try:
        run_date = datetime.strptime(run_date_str, "%Y-%m-%d").date()
    except ValueError:
        run_date = date.today()

    return JsonResponse({
        "date": run_date.isoformat(),
        "candles": DailyCandle.objects.filter(date=run_date).count(),
        "features": DailyFeature.objects.filter(date=run_date).count(),
        "labels": PredictionLabel.objects.filter(date=run_date).count(),
        "rankings": DailyRanking.objects.filter(date=run_date).count(),
        "models": ModelRun.objects.count(),
    })
