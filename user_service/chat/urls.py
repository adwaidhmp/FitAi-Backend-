from chat.views import (
    ChatHistoryView,
    SendMediaMessageView,
    SendTextMessageView,
    UserChatRoomListView,
)
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .user_trainer_vcall_view import (
    AcceptCallView, EndCallView, StartCallView,
)

urlpatterns = [
    path("rooms/", UserChatRoomListView.as_view()),
    path("rooms/<uuid:room_id>/messages/", ChatHistoryView.as_view()),
    path("send/text/", SendTextMessageView.as_view()),
    path("send/media/", SendMediaMessageView.as_view()),

    path(
        "calls/start/<uuid:room_id>/",
        StartCallView.as_view(),
        name="start-call",
    ),

    # accept incoming call
    path(
        "calls/<uuid:call_id>/accept/",
        AcceptCallView.as_view(),
        name="accept-call",
    ),

    # end active or ringing call
    path(
        "calls/<uuid:call_id>/end/",
        EndCallView.as_view(),
        name="end-call",
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
