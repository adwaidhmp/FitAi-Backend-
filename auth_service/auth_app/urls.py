from django.urls import path

from .admin_trainer_views import AdminApproveTrainerView, AdminTrainerListView
from .admin_user_views import AdminUserListView, AdminUserStatusView
from .user_trainer_views import (ApprovedTrainerListView, BulkUserInfoView,
                                 UsersByIdsView)
from .views import (ForgotPasswordConfirmView, ForgotPasswordRequestView,
                    GoogleLoginView, LoginView, LogoutView, ProfileEditView,
                    ProfileView, RequestOtpView, TrainerProfileView,
                    TrainerRegisterView, UserRegisterView)

urlpatterns = [
    path("request-otp/", RequestOtpView.as_view(), name="request-otp"),
    path("register/", UserRegisterView.as_view(), name="register-user"),
    path("register/trainer/", TrainerRegisterView.as_view(), name="register-trainer"),
    path("login/", LoginView.as_view(), name="login"),
    path("google/", GoogleLoginView.as_view()),
    path("logout/", LogoutView.as_view(), name="logout"),
    # user profile
    path("info/", ProfileView.as_view(), name="info"),
    path("info/edit/", ProfileEditView.as_view(), name="edit-info"),
    path(
        "reset-password/request-otp/",
        ForgotPasswordRequestView.as_view(),
        name="forgot-password-request-otp",
    ),
    path(
        "reset-password/confirm/",
        ForgotPasswordConfirmView.as_view(),
        name="forgot-password-confirm",
    ),
    # trainer profile
    path("trainer/info/", TrainerProfileView.as_view(), name="trainer-info"),
    path("trainer/info/edit/", ProfileEditView.as_view(), name="trainer-info-edit"),
    # service urls from admin service
    path("internal/admin/users/", AdminUserListView.as_view()),
    path("internal/admin/users/<uuid:user_id>/status/", AdminUserStatusView.as_view()),
    # service urls from trainer service
    path("internal/admin/trainers/", AdminTrainerListView.as_view()),
    path(
        "internal/admin/trainers/<uuid:user_id>/approve/",
        AdminApproveTrainerView.as_view(),
    ),
    path(
        "internal/users/bulk/",
        BulkUserInfoView.as_view(),
    ),
    # service urls from user service
    path(
        "internal/trainers/approved/",
        ApprovedTrainerListView.as_view(),
    ),
    path(
        "internal/users/by-ids/",
        UsersByIdsView.as_view(),
    ),
]
