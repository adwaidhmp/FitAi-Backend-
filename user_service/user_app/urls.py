from django.urls import path

from .user_trainer_view import (ApprovedTrainerListView,
                                ApprovedUsersForTrainerView, DecideBookingView,
                                PendingClientsTrainer)
from .views import (BookTrainerView, MyTrainersView, ProfileChoicesView,
                    RemoveTrainerView, UserProfileView)
from .user_diet_ai_view import (GenerateDietPlanView,FollowMealFromPlanView,LogCustomMealWithAIView,
                                SkipMealView,UpdateWeightView,CurrentDietPlanView,LogExtraMealView)

from .diet_analytics_view import (TodayMealStatusView,DailyProgressView,WeeklyProgressView,MonthlyProgressView)
from .user_workout_view import (GenerateWorkoutView,GetCurrentWorkoutView,LogWorkoutExerciseView,GetTodayWorkoutLogsView)
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

    #urls for ai diet plan follow
    path("diet/generate/", GenerateDietPlanView.as_view()),
    path("diet-plan/", CurrentDietPlanView.as_view()),
    path("diet/follow-meal/", FollowMealFromPlanView.as_view()),
    path("diet/log-custom-meal/", LogCustomMealWithAIView.as_view()),
    path("diet/skip-meal/", SkipMealView.as_view()),
    path("diet/extra-meal/",LogExtraMealView.as_view()),
    path("diet/update-weight/", UpdateWeightView.as_view()),
    path("diet/today/",TodayMealStatusView.as_view()),

    #diet graphs and analysis urls will be here
    path("progress/daily/", DailyProgressView.as_view()),
    path("progress/weekly/", WeeklyProgressView.as_view()),
    path("progress/monthly/", MonthlyProgressView.as_view()),

    #workout generation ai
    path("workout/generate/", GenerateWorkoutView.as_view()),
    path("workout/current/", GetCurrentWorkoutView.as_view()),
    path("workout/log/", LogWorkoutExerciseView.as_view()),
    path("workout/logs/today/", GetTodayWorkoutLogsView.as_view()),
]

