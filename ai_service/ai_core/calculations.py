from datetime import date


def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )


def calculate_bmr(weight, height, age, gender):
    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5
    return 10 * weight + 6.25 * height - 5 * age - 161


def activity_multiplier(level):
    return {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }.get(level, 1.2)


def target_calories(tdee, goal):
    if goal == "cutting":
        return tdee - 400
    if goal == "bulking":
        return tdee + 300
    return tdee


def calculate_macros(calories, weight, goal):
    protein = weight * (2.2 if goal == "cutting" else 1.8)
    fat = calories * 0.25 / 9
    carbs = (calories - (protein * 4 + fat * 9)) / 4

    return {
        "protein_g": round(protein),
        "fat_g": round(fat),
        "carbs_g": round(carbs),
    }
