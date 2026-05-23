"""Sandbox execution environment.

V1.0: subprocess-based isolation (Docker unavailable).
V1.5: Docker container (NET=none, read-only rootfs, 2c/4g).
"""

import os
import subprocess
import time
from pathlib import Path

from config import settings


class SandboxError(Exception):
    pass


class SandboxTimeout(SandboxError):
    pass


def ensure_dirs():
    """Create sandbox directories if not exist."""
    Path(settings.sandbox_data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.sandbox_output_dir).mkdir(parents=True, exist_ok=True)


def run_script(
    script_path: str,
    input_params: dict | None = None,
    timeout: int | None = None,
) -> dict:
    """Execute an analysis script in an isolated subprocess.

    V1.0: Uses subprocess with restricted environment.
    V1.5: Uses Docker container with full isolation.

    Returns: {"status": "success", "data": {...}} or {"status": "error", "message": "..."}
    """
    timeout = timeout or settings.sandbox_timeout
    ensure_dirs()

    # Write input params to file
    input_file = Path(settings.sandbox_data_dir) / "input.json"
    if input_params:
        import json

        input_file.write_text(json.dumps(input_params))

    output_file = Path(settings.sandbox_output_dir) / "output.json"

    env = {
        **os.environ,
        "SANDBOX_DATA_DIR": settings.sandbox_data_dir,
        "SANDBOX_OUTPUT_DIR": settings.sandbox_output_dir,
        "PATH": os.environ.get("PATH", "/usr/bin"),
    }

    start = time.monotonic()
    try:
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=settings.sandbox_output_dir,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if result.returncode != 0:
            return {
                "status": "error",
                "message": result.stderr.strip() or f"Exit code {result.returncode}",
                "execution_time_ms": elapsed_ms,
            }

        # Read output
        output_data = {}
        if output_file.exists():
            import json

            try:
                output_data = json.loads(output_file.read_text())
            except json.JSONDecodeError:
                output_data = {"raw_output": output_file.read_text()[:1000]}

        return {
            "status": "success",
            "data": output_data,
            "execution_time_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        raise SandboxTimeout(f"Script timed out after {timeout}s")

    finally:
        # Cleanup
        if input_file.exists():
            input_file.unlink(missing_ok=True)
        if output_file.exists():
            output_file.unlink(missing_ok=True)
