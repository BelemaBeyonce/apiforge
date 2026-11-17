import pytest

from app.schemas import Criterion
from app.services.evaluator import evaluate


@pytest.mark.parametrize(
    "kind,response,reference,case,expected",
    [
        ("exact", " 42 ", "42", True, 100),
        ("exact", "ABC", "abc", True, 0),
        ("exact", "Straße", "STRASSE", False, 100),
        ("contains", "return sorted(items)", "sorted", True, 100),
        ("exact", "prefix42", "42", True, 0),
        ("contains", "hello", "missing", False, 0),
    ],
)
def test_comparison(kind, response, reference, case, expected):
    score, feedback = evaluate(
        response, [Criterion(name="check", kind=kind, reference=reference, case_sensitive=case)]
    )
    assert score == expected
    assert feedback[0]["passed"] == (expected == 100)


def test_weighted_score_and_determinism():
    criteria = [
        Criterion(name="a", kind="contains", reference="yes", weight=2),
        Criterion(name="b", kind="exact", reference="no"),
    ]
    assert evaluate("yes", criteria)[0] == 66.67
    assert evaluate("yes", criteria) == evaluate("yes", criteria)


def test_code_is_inert(tmp_path):
    target = tmp_path / "must-not-exist"
    response = f"__import__('pathlib').Path('{target}').touch()"
    assert (
        evaluate(response, [Criterion(name="literal", kind="exact", reference=response)])[0] == 100
    )
    assert not target.exists()
