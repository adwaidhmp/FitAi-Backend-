class GuardrailError(Exception):
    pass


def validate_profile_for_diet(profile: dict, allow_medical: bool = False):
    required = [
        "dob",
        "gender",
        "height_cm",
        "weight_kg",
        "target_weight_kg",
        "goal",
        "activity_level",
    ]

    for field in required:
        if not profile.get(field):
            raise GuardrailError(f"{field} is required")

    medical_conditions = profile.get("medical_conditions", [])

    if medical_conditions and not allow_medical:
        raise GuardrailError("Diet plan cannot be generated due to medical conditions")

    age = profile.get("age")
    if age and (age < 16 or age > 65):
        raise GuardrailError("Age not supported for AI diet")
