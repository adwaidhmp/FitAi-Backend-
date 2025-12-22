

def build_payload_from_profile(profile):

    medical_conditions = profile.medical_conditions or []
    diet_mode = "medical_safe" if medical_conditions else "normal"
    
    return {
        "dob": profile.dob.isoformat(),
        "gender": profile.gender,
        "height_cm": float(profile.height_cm),
        "weight_kg": float(profile.weight_kg),
        "goal": profile.goal,
        "activity_level": profile.activity_level,
        "diet_constraints": profile.diet_constraints or [],
        "allergies": profile.allergies or [],
        "medical_conditions": medical_conditions,
        "diet_mode": diet_mode,
    }