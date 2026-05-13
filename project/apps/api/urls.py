from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("prediction/", views.prediction_page, name="prediction"),
    path("trigger/pipeline/", views.trigger_pipeline, name="trigger_pipeline"),
    path("trigger/ranking/", views.trigger_ranking_only, name="trigger_ranking"),
    path("trigger/catch-up/", views.trigger_catch_up, name="trigger_catch_up"),
    path("status/", views.pipeline_status, name="pipeline_status"),
]
