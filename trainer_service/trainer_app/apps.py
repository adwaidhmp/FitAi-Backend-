from django.apps import AppConfig


class TrainerAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trainer_app"

    def ready(self):
        from trainer_service.firebase.firebase_admin import initialize_firebase
        initialize_firebase()

