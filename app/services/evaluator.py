from app.schemas import Criterion

ENGINE_VERSION = "deterministic-v1"


def evaluate(response: str, criteria: list[Criterion]):
    """Compare inert text. Never import, compile or execute submissions."""
    feedback = []
    earned = 0
    for criterion in criteria:
        actual, reference = response.strip(), criterion.reference.strip()
        if not criterion.case_sensitive:
            actual, reference = actual.casefold(), reference.casefold()
        passed = actual == reference if criterion.kind == "exact" else reference in actual
        points = criterion.weight if passed else 0
        earned += points
        feedback.append(
            {
                "criterion": criterion.name,
                "passed": passed,
                "earned_weight": points,
                "possible_weight": criterion.weight,
                "message": "Reference matched" if passed else "Reference did not match",
            }
        )
    return round(100 * earned / sum(c.weight for c in criteria), 2), feedback
