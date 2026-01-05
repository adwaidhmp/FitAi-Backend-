from django.urls import path

from .views import GenerateWorkoutAPIView

urlpatterns = [path("generate/", GenerateWorkoutAPIView.as_view())]
