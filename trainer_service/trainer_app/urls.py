from django.urls import path

from .admin_trainer_views import AdminTrainerProfileView
from .user_trainer_views import TrainerProfilesByUserIdsView
from .views import (
    ApprovedUsersView,
    DecideBookingView,
    PendingClientsView,
    TrainerProfileView,
)
from .trainer_user_chat_view import(
    TrainerChatRoomListProxyView,
    TrainerChatHistoryProxyView,
    TrainerSendTextMessageProxyView,
    TrainerSendMediaProxyView,
)

from .trainer_user_call_view import(
    TrainerStartCallView,
    TrainerAcceptCallView,
    TrainerEndCallView,
    )

from .ueserdata_trainer_view import TrainerUserOverviewProxyView    

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
        "bookings/<uuid:booking_id>/decision/",
        DecideBookingView.as_view(),
    ),
    path(
        "approved-users/",
        ApprovedUsersView.as_view(),
    ),

    #chat service urls
    path("chat/rooms/", TrainerChatRoomListProxyView.as_view()),
    path("chat/rooms/<uuid:room_id>/messages/", TrainerChatHistoryProxyView.as_view()),
    path("chat/send/text/", TrainerSendTextMessageProxyView.as_view()),
    path("chat/send/media/", TrainerSendMediaProxyView.as_view()),

    #call service urls
    path(
        "calls/start/<uuid:room_id>/",
        TrainerStartCallView.as_view(),
        name="trainer-start-call",
    ),

    path(
        "calls/<uuid:call_id>/accept/",
        TrainerAcceptCallView.as_view(),
        name="trainer-accept-call",
    ),

    path(
        "calls/<uuid:call_id>/end/",
        TrainerEndCallView.as_view(),
        name="trainer-end-call",
    ),

    #user data over view proxy
    
    path(
        "users/<uuid:user_id>/overview/",
        TrainerUserOverviewProxyView.as_view(),
        name="trainer-user-overview-proxy",
    ),
    ]


