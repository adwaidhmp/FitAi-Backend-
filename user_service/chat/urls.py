from chat.views import (
    ChatHistoryView,
    SendMessageView,
    SendTextMessageView,
    UserChatRoomListView,
)
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

urlpatterns = [
    path("rooms/", UserChatRoomListView.as_view()),
    path("rooms/<uuid:room_id>/messages/", ChatHistoryView.as_view()),
    path("send/text/", SendTextMessageView.as_view()),
    path("send/media/", SendMessageView.as_view()),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
