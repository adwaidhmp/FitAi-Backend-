from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import razorpay
from .models import PremiumPlan, UserProfile
from .permissions import IsAdmin
from rest_framework import status
from django.conf import settings
from datetime import timedelta
from django.utils import timezone



class AdminPremiumPlanView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        """
        List ALL premium plans (admin view)
        """
        plans = PremiumPlan.objects.all().order_by("plan")

        return Response({
            "plans": [
                {
                    "code": p.plan,
                    "price": p.price,
                    "duration_days": p.duration_days,
                    "is_active": p.is_active,
                }
                for p in plans
            ]
        })

    def post(self, request):
        """
        Create or Update Premium Plan
        """
        plan_code = request.data.get("plan")
        price = request.data.get("price")
        is_active = request.data.get("is_active", True)

        if not plan_code or price is None:
            return Response(
                {"error": "plan and price are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan, created = PremiumPlan.objects.update_or_create(
            plan=plan_code,
            defaults={
                "price": price,
                "is_active": is_active,
            },
        )

        return Response(
            {
                "message": "Plan created" if created else "Plan updated",
                "plan": {
                    "code": plan.plan,
                    "price": plan.price,
                    "duration_days": plan.duration_days,
                    "is_active": plan.is_active,
                },
            },
            status=status.HTTP_200_OK,
        )



class PremiumPlansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = PremiumPlan.objects.filter(is_active=True)

        data = []
        for plan in plans:
            data.append({
                "code": plan.plan,                 # weekly / monthly
                "label": plan.plan.capitalize(),   # Weekly / Monthly
                "price": plan.price,
                "duration_days": plan.duration_days,
                "features": [
                    "Chat with approved trainers",
                    "Video call with trainers",
                    "Priority support",
                ],
            })

        return Response({"plans": data})
    

    
class CreatePremiumOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_code = request.data.get("plan")

        plan = PremiumPlan.objects.filter(
            plan=plan_code,
            is_active=True
        ).first()

        if not plan:
            return Response(
                {"error": "Invalid or inactive plan"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        order = client.order.create({
            "amount": plan.price * 100,  # paise
            "currency": "INR",
            "payment_capture": 1,
        })

        return Response({
            "order_id": order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount": plan.price,
            "currency": "INR",
            "plan": plan.plan,
        })



class VerifyPremiumPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"],
            })
        except Exception:
            return Response(
                {"error": "Payment verification failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan = PremiumPlan.objects.get(plan=data["plan"])

        profile, _ = UserProfile.objects.get_or_create(
            user_id=request.user.id
        )

        now = timezone.now()

        if profile.premium_expires_at and profile.premium_expires_at > now:
            profile.premium_expires_at += timedelta(days=plan.duration_days)
        else:
            profile.premium_expires_at = now + timedelta(days=plan.duration_days)

        profile.is_premium = True
        profile.save()

        return Response({"status": "premium_activated"})