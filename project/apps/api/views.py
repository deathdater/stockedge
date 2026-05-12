from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from project.apps.core.pipeline import run_daily_ranking_pipeline
from project.apps.rankings.models import DailyRanking


@require_http_methods(["GET", "POST"])
def dashboard(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        run_daily_ranking_pipeline(run_date=date.today())
        return redirect("api:dashboard")

    rankings = DailyRanking.objects.filter(date=date.today()).order_by("rank")[:25]
    return render(request, "api/dashboard.html", {"rankings": rankings, "today": date.today()})


@require_GET
def prediction_page(request: HttpRequest) -> HttpResponse:
    symbol = request.GET.get("symbol", "").upper().strip()
    prediction = None
    if symbol:
        prediction = get_object_or_404(DailyRanking.objects.order_by("-date"), symbol=symbol)
    return render(request, "api/prediction.html", {"symbol": symbol, "prediction": prediction})
