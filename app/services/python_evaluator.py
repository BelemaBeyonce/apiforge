from app.services.syntax_checker import check_syntax
from app.services.concept_checker import check_concepts

ENGINE_VERSION = "python-static-v1"


def evaluate_python(code: str, config: dict):
    syntax_enabled = config.get("syntax_check", True)
    required = config.get("required_concepts", [])

    feedback = []
    earned = 0
    possible = 0

    syntax = check_syntax(code)

    if syntax_enabled:
        possible += 40

        if syntax["passed"]:
            earned += 40

        feedback.append({
            "criterion": "Python Syntax",
            "passed": syntax["passed"],
            "earned_weight": 40 if syntax["passed"] else 0,
            "possible_weight": 40,
            "category": "syntax",
            "contribution": 40 if syntax["passed"] else 0,
            "reason": "valid_syntax" if syntax["passed"] else "syntax_error",
            "message": syntax["message"],
        })

    if required:
        possible += 60

        if syntax["passed"]:
            concepts = check_concepts(code, required)
            results = concepts["results"]
        else:
            results = {concept: False for concept in required}

        per_concept = 60 / len(required)

        for concept in required:
            passed = results[concept]

            if passed:
                earned += per_concept

            feedback.append({
                "criterion": f"Concept: {concept}",
                "passed": passed,
                "earned_weight": 1 if passed else 0,
                "possible_weight": 1,
                "category": "concepts",
                "contribution": round(per_concept if passed else 0, 4),
                "reason": "concept_detected" if passed else "concept_missing",
                "message": (
                    f"Required concept '{concept}' detected"
                    if passed else
                    f"Required concept '{concept}' not detected"
                ),
            })

    if possible == 0:
        return 0.0, feedback

    score = round((earned / possible) * 100, 2)

    return score, feedback