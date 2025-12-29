# chat/urls.py
from django.urls import path
from .views import UploadMessageView,ChatHistoryView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("chat/upload/", UploadMessageView.as_view()),
    path("chat/history/<uuid:room_id>/", ChatHistoryView.as_view()),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)