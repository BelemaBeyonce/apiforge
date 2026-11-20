import json
from app.services.code_runner import run_python


def evaluate_script(code: str, expected_output: str) -> dict:
    result = run_python(code)

    if not result["passed"]:
        return {
            "passed": False,
            "score": 0,
            "message": "Program execution failed",
            "execution": result,
        }

    actual = result["stdout"].strip()
    expected = expected_output.strip()

    passed = actual == expected

    return {
        "passed": passed,
        "score": 100 if passed else 0,
        "message": (
            "Program output matched expected output"
            if passed
            else "Program output did not match expected output"
        ),
        "expected": expected,
        "actual": actual,
    }

def evaluate_script_tests(
    code: str,
    test_cases: list[dict],
) -> dict:
    """
    Evaluate a script against multiple expected outputs.

    Each test case must contain:
        name: descriptive test name
        expected_output: expected stdout

    This version is for scripts without varying inputs.
    """

    if not test_cases:
        raise ValueError("At least one test case is required")

    execution = run_python(code)

    results = []

    for test in test_cases:
        expected = test["expected_output"].strip()
        actual = execution["stdout"].strip()

        passed = (
            execution["passed"]
            and actual == expected
        )

        results.append({
            "name": test["name"],
            "passed": passed,
            "expected": expected,
            "actual": actual,
        })

    passed_count = sum(
        result["passed"] for result in results
    )

    score = round(
        passed_count / len(test_cases) * 100,
        2,
    )

    return {
        "score": score,
        "passed_tests": passed_count,
        "total_tests": len(test_cases),
        "results": results,
    }

import json
from app.services.code_runner import run_python


def evaluate_function_tests(
    code: str,
    function_name: str,
    test_cases: list[dict],
) -> dict:
    if not function_name.isidentifier():
        raise ValueError("Invalid function name")

    if not test_cases:
        raise ValueError("At least one test case is required")

    results = []

    for test in test_cases:
        arguments = test.get("args", [])
        expected = test["expected"]

        # The test arguments are supplied by the trusted evaluator.
        # This is an initial local prototype.
        harness = f"""
import json

namespace = {{}}
student_code = {json.dumps(code)}
exec(compile(student_code, "<submission>", "exec"), namespace)

function = namespace[{json.dumps(function_name)}]
arguments = json.loads({json.dumps(json.dumps(arguments))})

result = function(*arguments)
print(json.dumps(result))
"""

        execution = run_python(harness)

        actual = None
        passed = False

        if execution["passed"]:
            try:
                actual = json.loads(execution["stdout"])
                passed = actual == expected
            except (ValueError, TypeError):
                pass

        results.append({
            "name": test["name"],
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "error": (
                execution["stderr"]
                if not execution["passed"]
                else None
            ),
        })

    passed_count = sum(
        item["passed"] for item in results
    )

    return {
        "score": round(
            passed_count / len(test_cases) * 100, 2
        ),
        "passed_tests": passed_count,
        "total_tests": len(test_cases),
        "results": results,
    }