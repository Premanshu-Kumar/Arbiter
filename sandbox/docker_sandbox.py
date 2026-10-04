"""
Docker Sandbox — Phase 7

Provides a Docker-based code execution sandbox for stronger isolation than
the default in-process executor. Falls back gracefully to the local SafeExecutor
if Docker is not available.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import subprocess
import tempfile
import os
import json
import time
import shutil


class DockerSandboxConfig:
    """Configuration for the Docker sandbox"""

    def __init__(
        self,
        image: str = "python:3.11-slim",
        timeout_seconds: int = 30,
        memory_limit: str = "256m",
        cpu_quota: int = 50000,  # 50% of one CPU
        network_disabled: bool = True,
        read_only_fs: bool = False,
        allowed_imports: Optional[list] = None,
    ):
        self.image = image
        self.timeout_seconds = timeout_seconds
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.network_disabled = network_disabled
        self.read_only_fs = read_only_fs
        self.allowed_imports = allowed_imports or [
            "pandas",
            "numpy",
            "json",
            "math",
            "statistics",
            "datetime",
            "collections",
            "itertools",
            "re",
        ]


class DockerSandbox:
    """
    Executes Python code inside an isolated Docker container.

    Features:
        - Memory and CPU limits
        - Network disabled by default
        - Temporary filesystem mount for data exchange
        - Automatic container cleanup
        - Graceful fallback when Docker is unavailable

    Usage:
        sandbox = DockerSandbox()
        result = sandbox.execute_python(code, df)
    """

    DOCKER_AVAILABLE: Optional[bool] = None  # cached at class level

    def __init__(self, config: Optional[DockerSandboxConfig] = None):
        self.config = config or DockerSandboxConfig()
        self._docker_available = self._check_docker()

    # ------------------------------------------------------------------
    #  Docker availability
    # ------------------------------------------------------------------

    def _check_docker(self) -> bool:
        """Check if Docker daemon is running and accessible"""
        if DockerSandbox.DOCKER_AVAILABLE is not None:
            return DockerSandbox.DOCKER_AVAILABLE

        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
                text=True,
            )
            available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            available = False

        DockerSandbox.DOCKER_AVAILABLE = available
        print(f"🐳 Docker available: {available}")
        return available

    @property
    def is_available(self) -> bool:
        return self._docker_available

    # ------------------------------------------------------------------
    #  Python execution
    # ------------------------------------------------------------------

    def execute_python(
        self,
        code: str,
        df_parquet_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code inside a Docker container.

        Args:
            code: Python code string to execute
            df_parquet_path: Path to a Parquet file with the input DataFrame.
                             If provided, the container can load it as `df`.

        Returns:
            dict with: success, result (JSON-serialisable), stdout, stderr, error, latency_ms
        """
        if not self._docker_available:
            return {
                "success": False,
                "error": "Docker is not available on this system",
                "docker_available": False,
            }

        # Create a temporary working directory
        work_dir = tempfile.mkdtemp(prefix="agent_sandbox_")

        try:
            # Write the user code
            code_path = os.path.join(work_dir, "user_code.py")
            runner_path = os.path.join(work_dir, "runner.py")

            with open(code_path, "w") as f:
                f.write(code)

            # Copy DataFrame if provided
            if df_parquet_path and os.path.exists(df_parquet_path):
                shutil.copy(df_parquet_path, os.path.join(work_dir, "data.parquet"))

            # Write runner script that captures output
            runner_code = self._build_runner(has_df=df_parquet_path is not None)
            with open(runner_path, "w") as f:
                f.write(runner_code)

            # Build docker run command
            cmd = self._build_docker_command(work_dir)

            start = time.perf_counter()
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.config.timeout_seconds + 5,
                text=True,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode != 0:
                return {
                    "success": False,
                    "error": stderr or f"Container exited with code {proc.returncode}",
                    "stdout": stdout,
                    "stderr": stderr,
                    "latency_ms": round(latency_ms, 1),
                    "docker_available": True,
                }

            # Parse the JSON result from stdout
            result = self._parse_output(stdout)
            result["latency_ms"] = round(latency_ms, 1)
            result["docker_available"] = True
            return result

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out after {self.config.timeout_seconds}s",
                "latency_ms": self.config.timeout_seconds * 1000,
                "docker_available": True,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "docker_available": True,
            }
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _build_runner(self, has_df: bool) -> str:
        """Build the runner script that wraps user code"""
        df_loader = (
            "import pandas as pd\ndf = pd.read_parquet('/sandbox/data.parquet')\n"
            if has_df
            else ""
        )

        return f"""
import sys
import json
import traceback
import pandas as pd
import numpy as np

{df_loader}

result = None
error = None

try:
    exec(open('/sandbox/user_code.py').read(), {{'df': df if 'df' in dir() else None}})
    # Try to extract 'result' variable from exec'd code
    local_vars = {{}}
    exec(open('/sandbox/user_code.py').read(), {{'df': df if 'df' in dir() else None}}, local_vars)
    result = local_vars.get('result')
except Exception as e:
    error = traceback.format_exc()

# Serialise result
def serialise(obj):
    if isinstance(obj, pd.DataFrame):
        return {{'_type': 'dataframe', 'data': obj.to_dict(orient='records'), 'columns': obj.columns.tolist()}}
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)

output = {{
    'success': error is None,
    'result': None if error else serialise(result),
    'error': error,
}}

print(json.dumps(output))
"""

    def _build_docker_command(self, work_dir: str) -> list:
        """Build the docker run command"""
        cmd = [
            "docker", "run",
            "--rm",  # Remove container after exit
            "--name", f"analyst_sandbox_{int(time.time())}",
            f"--memory={self.config.memory_limit}",
            f"--cpu-quota={self.config.cpu_quota}",
            "--pids-limit=100",
            "--ulimit", "nofile=256:256",
            "-v", f"{work_dir}:/sandbox:ro",  # Mount working dir read-only
            "--workdir", "/sandbox",
        ]

        if self.config.network_disabled:
            cmd.extend(["--network", "none"])

        # Install required packages and run
        cmd.extend([
            self.config.image,
            "sh", "-c",
            "pip install pandas numpy pyarrow -q && python /sandbox/runner.py",
        ])

        return cmd

    def _parse_output(self, stdout: str) -> Dict[str, Any]:
        """Parse the JSON output from the runner script"""
        # Find the last JSON line (in case there's other stdout)
        lines = stdout.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    # Reconstruct DataFrame if needed
                    if (
                        isinstance(data.get("result"), dict)
                        and data["result"].get("_type") == "dataframe"
                    ):
                        import pandas as pd
                        data["result"] = pd.DataFrame(
                            data["result"]["data"],
                            columns=data["result"]["columns"],
                        )
                    return data
                except json.JSONDecodeError:
                    pass

        return {
            "success": False,
            "error": f"Could not parse container output: {stdout[:500]}",
            "result": None,
        }

    # ------------------------------------------------------------------
    #  Image management
    # ------------------------------------------------------------------

    def pull_image(self) -> bool:
        """Pull the configured Docker image if not present"""
        if not self._docker_available:
            return False

        try:
            result = subprocess.run(
                ["docker", "pull", self.config.image],
                capture_output=True,
                timeout=120,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def image_exists(self) -> bool:
        """Check if the configured image is available locally"""
        if not self._docker_available:
            return False
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.config.image],
                capture_output=True,
                timeout=5,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def status(self) -> Dict[str, Any]:
        """Return sandbox status information"""
        return {
            "docker_available": self._docker_available,
            "image": self.config.image,
            "image_available": self.image_exists() if self._docker_available else False,
            "memory_limit": self.config.memory_limit,
            "timeout_seconds": self.config.timeout_seconds,
            "network_disabled": self.config.network_disabled,
        }
