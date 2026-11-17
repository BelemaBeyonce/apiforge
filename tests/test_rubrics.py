import pytest
from pydantic import ValidationError

from app.schemas import Criterion, RubricCategory, TaskInput
from app.services.evaluator import evaluate


@pytest.mark.parametrize(
    "response,pattern,case,score",
    [
        ("sum 42", r"sum \d+", True, 100),
        ("ABC", "abc", False, 100),
        ("abc", "^x$", True, 0),
        ("abc", "^abc$", True, 100),
    ],
)
def test_regex(response, pattern, case, score):
    assert (
        evaluate(
            response,
            [Criterion(name="pattern", kind="regex", reference=pattern, case_sensitive=case)],
        )[0]
        == score
    )


@pytest.mark.parametrize("pattern", ["[", "a" * 513, "(" * 21 + "x" + ")" * 21, "a{9999999}"])
def test_invalid_patterns(pattern):
    with pytest.raises(ValidationError):
        Criterion(name="invalid", kind="regex", reference=pattern)


def test_catastrophic_backtracking_is_bounded():
    score, feedback = evaluate(
        "a" * 20000 + "!", [Criterion(name="safe", kind="regex", reference="(a+)+$")]
    )
    assert score == 0
    assert feedback[0]["reason"] == "regex_time_limit"


def test_weighted_categories():
    criteria = [
        Criterion(name="a", kind="contains", reference="yes", category="correctness", weight=1),
        Criterion(name="b", kind="contains", reference="missing", category="style", weight=100),
    ]
    score, feedback = evaluate(
        "yes",
        criteria,
        [RubricCategory(name="correctness", weight=3), RubricCategory(name="style", weight=1)],
    )
    assert score == 75
    assert feedback[0]["contribution"] == 75


@pytest.mark.parametrize(
    "categories", [[{"name": "unused"}], [{"name": "general"}, {"name": "general"}]]
)
def test_invalid_categories(task_data, categories):
    with pytest.raises(ValidationError):
        TaskInput(**{**task_data, "categories": categories})


def test_comparison_and_api_regex(client, task_data):
    task_data["criteria"] = [{"name": "pattern", "kind": "regex", "reference": "^6$"}]
    task = client.post("/api/v1/tasks", json=task_data).json()
    url = f"/api/v1/tasks/{task['id']}/evaluations"
    first = client.post(url, json={"response": "6"}).json()
    second = client.post(url, json={"response": "7"}).json()
    result = client.get(f"/api/v1/evaluations/{first['id']}/compare/{second['id']}").json()
    assert result["score_delta"] == -100
    assert result["same_rubric"] is True
    assert client.get(f"/api/v1/evaluations/{first['id']}/compare/999").status_code == 404


def test_regex_budget_status_is_persisted(client, task_data):
    task_data["criteria"] = [{"name": "limited", "kind": "regex", "reference": "(a+)+$"}]
    task = client.post("/api/v1/tasks", json=task_data).json()
    result = client.post(
        f"/api/v1/tasks/{task['id']}/evaluations", json={"response": "a" * 20000 + "!"}
    )
    assert result.status_code == 201
    assert result.json()["status"] == "completed_with_limits"
    assert result.json()["feedback"][0]["reason"] == "regex_time_limit"
