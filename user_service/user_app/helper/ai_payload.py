

def build_payload_from_profile(profile):

    medical_conditions = profile.medical_conditions or []
    diet_mode = "medical_safe" if medical_conditions else "normal"
    
    return {
        "dob": profile.dob.isoformat(),
        "gender": profile.gender,
        "height_cm": float(profile.height_cm),
        "weight_kg": float(profile.weight_kg),
        "target_weight_kg": float(profile.target_weight_kg),
        "goal": profile.goal,
        "activity_level": profile.activity_level,
        "diet_constraints": profile.diet_constraints or [],
        "allergies": profile.allergies or [],
        "medical_conditions": medical_conditions,
        "diet_mode": diet_mode,
    }


def build_workout_ai_payload(
    *,
    profile,
    workout_type,
    exercise_count,
    min_duration,
    max_duration,
):
    payload = {
        "goal": profile.goal or "general_fitness",
        "experience": profile.exercise_experience or "beginner",
        "activity_level": profile.activity_level or "moderate",
        "workout_type": workout_type,
        "exercise_count": exercise_count,
        "min_duration": min_duration,
        "max_duration": max_duration,
    }

    if workout_type in ("strength", "mixed"):
        payload["equipment"] = profile.preferred_equipment or ["bodyweight"]

    return payload
