from ..models import MealLog


def meal_already_logged(user_id, date, meal_type):
    return MealLog.objects.filter(
        user_id=user_id,
        date=date,
        meal_type=meal_type,
    ).exists()
