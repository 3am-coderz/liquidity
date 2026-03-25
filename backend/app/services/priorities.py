from datetime import date


def infer_priority(category: str, due_date: date | None, amount: float, extracted_text: str | None = None) -> tuple[str, str]:
    today = date.today()
    days_until_due = (due_date - today).days if due_date else 7
    lowered = (extracted_text or "").lower()
    normalized_category = (category or "Operations").lower()

    if normalized_category in {"payroll", "legal"}:
        return "HIGH", f"{category} is treated as survival-critical and should be handled first."

    if any(keyword in lowered for keyword in ["urgent", "final notice", "disconnect", "penalty", "late fee", "overdue"]):
        return "HIGH", "The uploaded invoice contains urgency or penalty signals."

    if days_until_due <= 2:
        return "HIGH", "The due date is very close, so the bill should be prioritized."

    if normalized_category in {"rent", "tax", "utilities"}:
        return "MEDIUM", f"{category} affects ongoing operations and should stay near the top of the queue."

    if amount >= 50000:
        return "MEDIUM", "This is a large invoice, so it deserves early review even without immediate urgency."

    return "LOW", "No strong urgency markers were detected, so this can stay lower in the payment queue."


def priority_weights(priority_label: str) -> tuple[float, float, float, float, bool]:
    mapping = {
        "HIGH": (0.8, 0.95, 0.9, 0.75, True),
        "MEDIUM": (0.65, 0.7, 0.6, 0.55, False),
        "LOW": (0.45, 0.35, 0.3, 0.35, False),
    }
    return mapping.get(priority_label, mapping["LOW"])
