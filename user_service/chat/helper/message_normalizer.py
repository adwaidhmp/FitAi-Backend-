import uuid
import datetime

def normalize_for_ws(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    if isinstance(obj, dict):
        return {k: normalize_for_ws(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [normalize_for_ws(v) for v in obj]

    return obj
