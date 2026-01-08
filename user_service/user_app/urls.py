from django.urls import path

from .diet_analytics_view import (
    DailyProgressView,
    MonthlyProgressView,
    TodayMealStatusView,
    WeeklyProgressView,
)
from .user_diet_ai_view import (
    CurrentDietPlanView,
    FollowMealFromPlanView,
    GenerateDietPlanView,
    LogCustomMealWithAIView,
    LogExtraMealView,
    SkipMealView,
    UpdateWeightView,
)
from .user_trainer_view import (
    ApprovedTrainerListView,
    ApprovedUsersForTrainerView,
    PendingClientsTrainer,
    BookingDetailView,
)
from .user_workout_view import (
    GenerateWorkoutView,
    GetCurrentWorkoutView,
    GetTodayWorkoutLogsView,
    LogWorkoutExerciseView,
)
from .views import (
    BookTrainerView,
    MyTrainersView,
    ProfileChoicesView,
    RemoveTrainerView,
    UserProfileView,
)

from .trainer_userdata_view import TrainerUserOverviewView

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("choices/", ProfileChoicesView.as_view(), name="profile-choices"),
    path("trainers/approved/", ApprovedTrainerListView.as_view()),
    path("trainers/<uuid:trainer_user_id>/book/", BookTrainerView.as_view()),
    path("trainers/remove/", RemoveTrainerView.as_view()),
    path("my-trainers/", MyTrainersView.as_view()),

    # service url for trainer to see pending clients and approve booking

    path("training/pending/", PendingClientsTrainer.as_view()),
    path("training/bookings/approved/", ApprovedUsersForTrainerView.as_view()),
    path("training/bookings/<uuid:booking_id>/", BookingDetailView.as_view(),),
    # urls for ai diet plan follow

    path("diet/generate/", GenerateDietPlanView.as_view()),
    path("diet-plan/", CurrentDietPlanView.as_view()),
    path("diet/follow-meal/", FollowMealFromPlanView.as_view()),
    path("diet/log-custom-meal/", LogCustomMealWithAIView.as_view()),
    path("diet/skip-meal/", SkipMealView.as_view()),
    path("diet/extra-meal/", LogExtraMealView.as_view()),
    path("diet/update-weight/", UpdateWeightView.as_view()),
    path("diet/today/", TodayMealStatusView.as_view()),

    # diet graphs and analysis urls will be here

    path("progress/daily/", DailyProgressView.as_view()),
    path("progress/weekly/", WeeklyProgressView.as_view()),
    path("progress/monthly/", MonthlyProgressView.as_view()),

    # workout generation ai

    path("workout/generate/", GenerateWorkoutView.as_view()),
    path("workout/current/", GetCurrentWorkoutView.as_view()),
    path("workout/log/", LogWorkoutExerciseView.as_view()),
    path("workout/logs/today/", GetTodayWorkoutLogsView.as_view()),

    # trainer user data overview for trainers

    path(
        "trainer/users/<uuid:user_id>/overview/",
        TrainerUserOverviewView.as_view(),
        name="trainer-user-overview",
    ),
]
