from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_generator import generate_weekly_workout


class GenerateWorkoutAPIView(APIView):
    def post(self, request):
        data = request.data

        required = [
            "goal",
            "experience",
            "workout_type",
            "exercise_count",
            "min_duration",
            "max_duration",
        ]

        for key in required:
            if key not in data:
                return Response(
                    {"error": f"{key} missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ✅ FIX: normalize equipment
        if data["workout_type"] in ("strength", "mixed"):
            data["equipment"] = data.get("equipment") or ["bodyweight"]

        try:
            ai_result = generate_weekly_workout(
                profile_data=data,
                workout_type=data["workout_type"],
                exercise_count=data["exercise_count"],
                min_duration=data["min_duration"],
                max_duration=data["max_duration"],
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(ai_result, status=status.HTTP_200_OK)
