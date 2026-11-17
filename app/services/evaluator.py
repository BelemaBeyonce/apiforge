import regex

from app.schemas import Criterion, RubricCategory

ENGINE_VERSION = "deterministic-v2"
REGEX_TIMEOUT_SECONDS = 0.01


def evaluate(
    response: str, criteria: list[Criterion], categories: list[RubricCategory] | None = None
):
    """Bounded, inert text comparison; no code execution. Timeout scores that rule zero."""
    categories = categories or [RubricCategory(name="general")]
    weights = {category.name: category.weight for category in categories}
    totals = {name: sum(c.weight for c in criteria if c.category == name) for name in weights}
    category_weight = sum(weights.values())
    feedback = []
    raw_score = 0.0
    for criterion in criteria:
        actual, reference = response.strip(), criterion.reference.strip()
        reason = "matched"
        if criterion.kind == "regex":
            try:
                flags = 0 if criterion.case_sensitive else regex.IGNORECASE | regex.FULLCASE
                passed = (
                    regex.search(reference, actual, flags=flags, timeout=REGEX_TIMEOUT_SECONDS)
                    is not None
                )
            except TimeoutError:
                passed, reason = False, "regex_time_limit"
        else:
            if not criterion.case_sensitive:
                actual, reference = actual.casefold(), reference.casefold()
            passed = actual == reference if criterion.kind == "exact" else reference in actual
        if not passed and reason != "regex_time_limit":
            reason = {
                "exact": "exact_mismatch",
                "contains": "required_text_missing",
                "regex": "pattern_not_matched",
            }[criterion.kind]
        points = criterion.weight if passed else 0
        contribution = (
            100
            * points
            / totals[criterion.category]
            * weights[criterion.category]
            / category_weight
        )
        raw_score += contribution
        feedback.append(
            {
                "criterion": criterion.name,
                "passed": passed,
                "earned_weight": points,
                "possible_weight": criterion.weight,
                "category": criterion.category,
                "contribution": round(contribution, 4),
                "reason": reason,
                "message": "Reference matched"
                if passed
                else {
                    "regex_time_limit": "Regex exceeded its time budget; criterion scored zero",
                    "exact_mismatch": "Response differs from the exact reference",
                    "required_text_missing": "Required literal text was not found",
                    "pattern_not_matched": "Response did not match the regex pattern",
                }[reason],
            }
        )
    return round(raw_score, 2), feedback
