import ast


def check_syntax(code: str) -> dict:
    try:
        ast.parse(code)

        return {
            "passed": True,
            "error_type": None,
            "message": "Valid Python syntax",
            "line": None,
            "column": None,
        }

    except SyntaxError as error:
        return {
            "passed": False,
            "error_type": type(error).__name__,
            "message": error.msg,
            "line": error.lineno,
            "column": error.offset,
        }
