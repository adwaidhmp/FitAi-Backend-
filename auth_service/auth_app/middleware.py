# auth_app/middleware.py
class AllowPopupsCOOP:
    """Set Cross-Origin-Opener-Policy to allow popups to keep window.opener."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        return response
