
def validate_ai_workout(data, expected_count, min_total, max_total):
    sessions = data.get("sessions")
    if not sessions:
        raise ValueError("sessions missing")

    exercises = sessions[0].get("exercises", [])
    if len(exercises) != expected_count:
        raise ValueError("invalid exercise count")

    total_duration = sum(e["duration_sec"] for e in exercises)
    if total_duration < min_total * 60 or total_duration > max_total * 60:
        raise ValueError("invalid total duration")

    for e in exercises:
        if e["intensity"] not in ["low", "medium", "high"]:
            raise ValueError("invalid intensity")
