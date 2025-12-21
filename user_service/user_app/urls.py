from django.urls import path

from .user_trainer_view import (ApprovedTrainerListView,
                                ApprovedUsersForTrainerView, DecideBookingView,
                                PendingClientsTrainer)
from .views import (BookTrainerView, MyTrainersView, ProfileChoicesView,
                    RemoveTrainerView, UserProfileView)

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("choices/", ProfileChoicesView.as_view(), name="profile-choices"),
    path("trainers/approved/", ApprovedTrainerListView.as_view()),
    path("trainers/<uuid:trainer_user_id>/book/", BookTrainerView.as_view()),
    path("trainers/remove/", RemoveTrainerView.as_view()),
    path("my-trainers/", MyTrainersView.as_view()),

    # service url for trainer to see pending clients and approve booking
    path("training/pending/", PendingClientsTrainer.as_view()),
    path("training/booking/<uuid:booking_id>/", DecideBookingView.as_view()),
    path("training/bookings/approved/", ApprovedUsersForTrainerView.as_view()),
]
