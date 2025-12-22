from django.urls import path

from .user_trainer_view import (ApprovedTrainerListView,
                                ApprovedUsersForTrainerView, DecideBookingView,
                                PendingClientsTrainer)
from .views import (BookTrainerView, MyTrainersView, ProfileChoicesView,
                    RemoveTrainerView, UserProfileView)
from .user_diet_ai_view import (GenerateDietPlanView,FollowMealFromPlanView,LogCustomMealWithAIView,
                                SkipMealView,UpdateWeightView)

from .diet_analytics_view import (DailyCaloriesView,
                                 MonthlyCaloriesView,WeeklyProgressView,MonthlyWeightView,MonthlyCauseAnalysisView)

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
    path("diet/follow-meal/", FollowMealFromPlanView.as_view()),
    path("diet/log-custom-meal/", LogCustomMealWithAIView.as_view()),
    path("diet/skip-meal/", SkipMealView.as_view()),
    path("diet/update-weight/", UpdateWeightView.as_view()),

    #diet graphs and analysis urls will be here
    path("diet/daily-calories/", DailyCaloriesView.as_view()),
    path("diet/weekly-progress/", WeeklyProgressView.as_view()),
    path("diet/monthly-calories/", MonthlyCaloriesView.as_view()),
    path("diet/monthly-weight/", MonthlyWeightView.as_view()),
    path("diet/monthly-cause-analysis/", MonthlyCauseAnalysisView.as_view()),
]
