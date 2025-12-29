from django.urls import path

from .admin_trainer_views import AdminTrainerProfileView
from .user_trainer_views import TrainerProfilesByUserIdsView
from .views import (TrainerProfileView,ApprovedUsersView,
                    DecideBookingView, PendingClientsView)

urlpatterns = [
    path("profile/", TrainerProfileView.as_view(), name="trainer-profile"),
    # service url for admin
    path(
        "internal/admin/trainers/<uuid:user_id>/profile/",
        AdminTrainerProfileView.as_view(),
    ),
    path(
        "internal/trainers/by-user-ids/",
        TrainerProfilesByUserIdsView.as_view(),
    ),
    # service url for user for booking trainer and approving user
    path(
        "pending-clients/",
        PendingClientsView.as_view(),
    ),
    path(
        "bookings/<uuid:booking_id>/decison/",
        DecideBookingView.as_view(),
    ),
    path(
        "approved-users/",
        ApprovedUsersView.as_view(),
    ),
]

print("hai")