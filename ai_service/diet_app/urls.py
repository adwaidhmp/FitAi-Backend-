from django.urls import path

from .views import GenerateDietView, NutritionEstimateView

urlpatterns = [
    path("generate/", GenerateDietView.as_view()),
    path("estimate-nutrition/", NutritionEstimateView.as_view()),
]
