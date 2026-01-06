import requests
from django.conf import settings
from rest_framework.response import Response

USER_SERVICE_URL = settings.USER_SERVICE_URL


def forward_request(request, method, path, *, data=None, files=None, params=None):
    headers = {
        "Authorization": request.headers.get("Authorization"),
    }

    url = f"{USER_SERVICE_URL}{path}"

    prepared_files = None
    if files:
        prepared_files = {}
        for key, uploaded_file in files.items():
            uploaded_file.seek(0)
            prepared_files[key] = (
                uploaded_file.name,
                uploaded_file.read(),
                uploaded_file.content_type,
            )

    resp = requests.request(
        method=method,
        url=url,
        headers=headers,
        data=data,
        files=prepared_files,
        params=params,
        timeout=15,
    )

    if "application/json" in resp.headers.get("Content-Type", ""):
        return Response(resp.json(), status=resp.status_code)

    if resp.status_code < 400:
        return Response(status=resp.status_code)

    return Response(
        {"detail": resp.text or "Upstream service error"},
        status=resp.status_code,
    )