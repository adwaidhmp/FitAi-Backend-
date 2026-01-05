from rest_framework.pagination import CursorPagination


class ChatMessageCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"  # newest first
    cursor_query_param = "cursor"
