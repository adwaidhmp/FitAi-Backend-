# workout validators


def validate_ai_workout(data, expected_count, min_total, max_total):
    sessions = data.get("sessions")
    if not sessions:
        raise ValueError("sessions missing")

    exercises = sessions[0].get("exercises")
    if not exercises or len(exercises) != expected_count:
        raise ValueError("invalid exercise count")

    total_duration = sum(e.get("duration_sec", 0) for e in exercises)
    if not (min_total * 60 <= total_duration <= max_total * 60):
        raise ValueError("invalid total duration")

    for e in exercises:
        if e.get("intensity") not in ("low", "medium", "high"):
            raise ValueError("invalid intensity")
