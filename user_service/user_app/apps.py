from django.apps import AppConfig

class UserAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user_app"

    def ready(self):
        from user_service.firebase.firebase_admin import initialize_firebase
        initialize_firebase()