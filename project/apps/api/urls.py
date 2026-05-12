from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("prediction/", views.prediction_page, name="prediction"),
]
