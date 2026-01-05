# workout/utils.py
from datetime import date, timedelta


def get_week_range(today: date | None = None):
    """
    Returns (week_start, week_end)
    Week starts on Monday and ends on Sunday.
    """
    if today is None:
        today = date.today()

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    return week_start, week_end
