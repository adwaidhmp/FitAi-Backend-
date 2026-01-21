def evaluate_risk(intent: str, question: str) -> str:
    """
    Returns one of:
    - low
    - medium
    - high
    """

    # HIGH RISK: medical or health conditions
    if intent == "medical":
        return "high"

    # MEDIUM RISK: topics that are often misused
    if intent in ["weight_loss", "protein_supplement"]:
        return "medium"

    # LOW RISK: general fitness & nutrition
    if intent in ["nutrition", "workout", "general"]:
        return "low"

    # fallback
    return "low"
