from datetime import date


# -----------------------------
# AGE
# -----------------------------
def calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )


# -----------------------------
# BMR (Mifflin-St Jeor)
# -----------------------------
def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    if gender == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


# -----------------------------
# ACTIVITY MULTIPLIER
# -----------------------------
def activity_multiplier(level: str) -> float:
    return {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }.get(level, 1.2)


# -----------------------------
# TARGET CALORIES (TARGET-AWARE)
# -----------------------------
def target_calories(
    tdee: float,
    current_weight: float,
    target_weight: float,
    goal: str,
) -> int:
    """
    No timeline.
    Calories depend only on distance from target.
    """

    weight_gap = abs(current_weight - target_weight)

    # FAT LOSS
    if goal == "cutting":
        if current_weight <= target_weight:
            return round(tdee)  # maintenance (goal reached)

        if weight_gap <= 2:
            deficit_pct = 0.05
        elif weight_gap <= 6:
            deficit_pct = 0.15
        else:
            deficit_pct = 0.20

        return round(tdee * (1 - deficit_pct))

    # MUSCLE GAIN
    if goal == "bulking":
        if current_weight >= target_weight:
            return round(tdee)  # maintenance (goal reached)

        surplus_pct = 0.10
        return round(tdee * (1 + surplus_pct))

    # MAINTENANCE
    return round(tdee)


# -----------------------------
# MACROS (SAFE + SIMPLE)
# -----------------------------
def calculate_macros(calories: int, weight_kg: float, goal: str) -> dict:
    """
    Protein anchored to body weight.
    Fat fixed %.
    Carbs fill remaining calories.
    """

    if goal == "cutting":
        protein_g = weight_kg * 2.2
    elif goal == "bulking":
        protein_g = weight_kg * 1.8
    else:
        protein_g = weight_kg * 1.6

    fat_g = (calories * 0.25) / 9
    carbs_g = (calories - (protein_g * 4 + fat_g * 9)) / 4

    return {
        "protein_g": round(protein_g),
        "fat_g": round(fat_g),
        "carbs_g": round(carbs_g),
    }
