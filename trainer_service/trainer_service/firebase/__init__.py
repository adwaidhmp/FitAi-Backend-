import firebase_admin
from firebase_admin import credentials

# This function runs only once
def initialize_firebase():
    # Prevent re-initialization errors in Django reloads
    if not firebase_admin._apps:
        cred = credentials.Certificate(
            "credentials/firebase-admin.json"
        )
        firebase_admin.initialize_app(cred)
