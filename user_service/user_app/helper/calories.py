from decimal import ROUND_HALF_UP, Decimal

# All factors MUST be Decimal
INTENSITY_FACTOR = {
    "low": Decimal("0.035"),
    "medium": Decimal("0.05"),
    "high": Decimal("0.075"),
}


def calculate_calories(duration_sec, weight_kg, intensity):
    """
    duration_sec : int
    weight_kg    : Decimal (from Django model)
    intensity    : str ("low" | "medium" | "high")
    """

    # ❌ NEVER do duration_sec / 60 (creates float)
    minutes = Decimal(duration_sec) / Decimal("60")

    # weight_kg is already Decimal, but normalize anyway
    weight = Decimal(weight_kg)

    factor = INTENSITY_FACTOR[intensity]

    calories = minutes * weight * factor

    # Round properly instead of truncating
    return calories.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
