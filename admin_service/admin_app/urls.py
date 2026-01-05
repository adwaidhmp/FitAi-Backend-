from django.urls import path

from .views import (
    AdminApproveTrainerView,
    AdminTrainerDetailView,
    AdminTrainerListView,
    AdminUserListView,
    AdminUserStatusView,
)

urlpatterns = [
    path("users/", AdminUserListView.as_view()),
    path("users/<uuid:user_id>/status/", AdminUserStatusView.as_view()),
    path("trainers/", AdminTrainerListView.as_view()),
    path("trainers/<uuid:user_id>/", AdminTrainerDetailView.as_view()),
    path("trainers/<uuid:user_id>/approve/", AdminApproveTrainerView.as_view()),
]
