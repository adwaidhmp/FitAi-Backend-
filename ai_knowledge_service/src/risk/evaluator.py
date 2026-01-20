def evaluate_risk(intent: str, question: str) -> str:
    """
    Returns one of:
    - low
    - medium
    - high
    """

    # HIGH RISK: medical or explicitly unsafe behavior
    if intent in ["medical", "unsafe"]:
        return "high"

    # MEDIUM RISK: advice that can be misused if followed incorrectly
    if intent in ["nutrition", "workout"]:
        return "medium"

    # LOW RISK: informational or casual
    if intent in ["general", "chitchat"]:
        return "low"

    # Fallback (should never happen)
    return "low"
