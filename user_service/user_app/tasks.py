# user_app/tasks.py
from celery import shared_task
from .models import MealLog
from .helper.ai_client import estimate_nutrition


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 3},
)
def estimate_nutrition_task(self, meal_log_id):
    meal = MealLog.objects.get(id=meal_log_id)

    # idempotent
    if meal.calories > 0:
        return

    result = estimate_nutrition(", ".join(meal.items))
    total = result["total"]

    meal.calories = total.get("calories", 0)
    meal.protein = total.get("protein", 0)
    meal.carbs = total.get("carbs", 0)
    meal.fat = total.get("fat", 0)
    meal.save()

