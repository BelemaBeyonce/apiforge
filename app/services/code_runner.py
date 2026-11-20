import subprocess
import uuid
import tempfile


IMAGE = "python:3.12-slim"
MAX_OUTPUT = 10_000


def run_python(code: str, timeout: int = 5) -> dict:
    """
    Run Python code in a restricted Docker container.

    Development prototype only. Do not expose this runner
    to untrusted public submissions yet.
    """
    container_name = f"apiforge-{uuid.uuid4().hex}"
    command = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", "128m",
        "--memory-swap", "128m",
        "--cpus", "0.5",
        "--pids-limit", "32",
        "--user", "65534:65534",
        IMAGE,
        "python", "-I", "-B", "-c", code,
    ]

    try:
        with tempfile.TemporaryFile(mode="w+b") as stdout_file, \
            tempfile.TemporaryFile(mode="w+b") as stderr_file:

            result = subprocess.run(
                command,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=timeout,
                check=False,
            )

            stdout_file.seek(0)
            stderr_file.seek(0)

            stdout = stdout_file.read(MAX_OUTPUT).decode(
                "utf-8", errors="replace"
            )
            stderr = stderr_file.read(MAX_OUTPUT).decode(
                "utf-8", errors="replace"
            )
            
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            )

        return {
        "passed": result.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": result.returncode,
        "timed_out": False,
    }
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            timeout=10,
            check=False,
        )

        return {
            "passed": False,
            "stdout": "",
            "stderr": "Execution exceeded the time limit",
            "returncode": None,
            "timed_out": True,
        }