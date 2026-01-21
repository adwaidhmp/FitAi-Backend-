import joblib
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path

# -------------------------------------------------
# Paths
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "models"

CLASSIFIER_PATH = MODEL_DIR / "intent_classifier.joblib"
LABEL_ENCODER_PATH = MODEL_DIR / "intent_label_encoder.joblib"

# -------------------------------------------------
# Load model artifacts (ONCE at startup)
# -------------------------------------------------
clf = joblib.load(CLASSIFIER_PATH)
label_encoder = joblib.load(LABEL_ENCODER_PATH)

# -------------------------------------------------
# Sentence embedder (STRICT LOCAL LOAD, NO HF EVER)
# -------------------------------------------------
embedder = SentenceTransformer(
    "/app/models/all-MiniLM-L6-v2",
    local_files_only=True
)

# -------------------------------------------------
# Prediction function
# -------------------------------------------------
def predict_intent(text: str):
    """
    Predict intent and confidence margin for a given text.
    Returns: (intent: str, confidence: float)
    """

    if not text or not text.strip():
        return "chitchat", 1.0

    # Encode text
    emb = embedder.encode([text], normalize_embeddings=True)

    # Decision scores (LinearSVC has no predict_proba)
    scores = clf.decision_function(emb)[0]

    idx = int(np.argmax(scores))
    intent = label_encoder.inverse_transform([idx])[0]
    confidence = float(scores[idx])

    return intent, confidence


# -------------------------------------------------
# Local test (optional)
# -------------------------------------------------
if __name__ == "__main__":
    tests = [
        "Hi",
        "Thanks bro",
        "What is BMI?",
        "How many carbs do I need daily?",
        "How many reps for bench press?",
        "My knee hurts after workout",
        "How to lose 10kg in one week?"
    ]

    for t in tests:
        intent, conf = predict_intent(t)
        print(f"{t:45} → {intent:12} | confidence: {conf:.3f}")
