def classify_intent(question: str) -> str:
    q = question.lower()

    # 1️⃣ MEDICAL (strong signals only)
    if any(word in q for word in [
        "diabetes",
        "sugar problem",
        "bp",
        "blood pressure",
        "thyroid",
        "pcos",
        "pcod",
        "pregnant",
        "pregnancy",
        "heart problem",
        "asthma",
        "kidney problem",
        "liver problem",
        "doctor",
        "medicine",
        "medical problem",
        "health issue",
    ]):
        return "medical"

    # 2️⃣ PROTEIN / SUPPLEMENTS
    if any(word in q for word in [
        "protein",
        "protein powder",
        "whey",
        "whey protein",
        "isolate",
        "concentrate",
        "casein",
        "mass gainer",
        "supplement",
        "bcaa",
        "creatine",
        "lactose",
    ]):
        return "protein_supplement"

    # 3️⃣ WEIGHT LOSS
    if any(word in q for word in [
        "weight loss",
        "lose weight",
        "reduce weight",
        "fat loss",
        "belly fat",
        "lose fat",
        "slim",
        "slimming",
        "thin",
        "how to lose weight",
        "how reduce weight",
    ]):
        return "weight_loss"

    # 4️⃣ WORKOUT / GYM
    if any(word in q for word in [
        "gym",
        "workout",
        "exercise",
        "training",
        "cardio",
        "weights",
        "lifting",
        "running",
        "walking",
        "yoga",
        "home workout",
        "bodybuilding",
        "muscle",
    ]):
        return "workout"

    # 5️⃣ NUTRITION / FOOD
    if any(word in q for word in [
        "diet",
        "food",
        "eat",
        "eating",
        "meal",
        "calories",
        "carbs",
        "fat",
        "vitamin",
        "nutrition",
        "healthy food",
        "junk food",
        "indian food",
    ]):
        return "nutrition"

    # 6️⃣ GENERAL
    return "general"
