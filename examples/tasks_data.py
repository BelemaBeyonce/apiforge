TASK = {
    "title": "Explain stable sorting",
    "description": "Describe Python sorting and equal-item order.",
    "language": "python",
    "difficulty": "easy",
    "expected_outcome": "Mention sorted and stable ordering.",
    "categories": [{"name": "correctness", "weight": 3}, {"name": "explanation", "weight": 1}],
    "criteria": [
        {
            "name": "builtin",
            "kind": "contains",
            "reference": "sorted",
            "category": "correctness",
            "weight": 1,
        },
        {
            "name": "stability",
            "kind": "contains",
            "reference": "stable",
            "category": "explanation",
            "weight": 1,
        },
    ],
}
