import ast

CONCEPT_NODES = {
    "variables": (ast.Assign, ast.AnnAssign, ast.NamedExpr),
    "conditionals": (ast.If,),
    "for_loops": (ast.For, ast.AsyncFor),
    "while_loops": (ast.While,),
    "functions": (ast.FunctionDef, ast.AsyncFunctionDef),
    "classes": (ast.ClassDef,),
    "try_except": (ast.Try,),
    "list_comprehensions": (ast.ListComp,),
    "dict_comprehensions": (ast.DictComp,),
    "set_comprehensions": (ast.SetComp,),
    "imports": (ast.Import, ast.ImportFrom),
    "return_statements": (ast.Return,),
    "with_statements": (ast.With, ast.AsyncWith),
}


def check_concepts(code: str, required: list[str]) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return {
            "passed": False,
            "error": f"{type(error).__name__}: {error.msg}",
            "results": {},
        }

    results = {}

    for concept in required:
        if concept not in CONCEPT_NODES:
            raise ValueError(f"Unsupported concept: {concept}")

        found = any(isinstance(node, CONCEPT_NODES[concept]) for node in ast.walk(tree))

        results[concept] = found

    return {
        "passed": all(results.values()),
        "results": results,
    }
