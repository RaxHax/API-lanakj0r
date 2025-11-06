"""Ensure the Firebase CLI can find a Python virtualenv for deployments."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # /functions
VENV_DIR = BASE_DIR / "venv"
REQUIREMENTS_PATH = BASE_DIR / "requirements.txt"
MARKER_FILE = VENV_DIR / ".requirements-hash"


class EnsureVenvError(RuntimeError):
    """Raised when the helper cannot prepare the virtualenv."""


def _log(message: str) -> None:
    print(f"[ensure_venv] {message}")


def _hash_requirements(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _should_install(requirements_hash: str) -> bool:
    if not MARKER_FILE.exists():
        return True
    try:
        recorded = MARKER_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return True
    return recorded != requirements_hash


def _write_marker(requirements_hash: str) -> None:
    MARKER_FILE.write_text(requirements_hash, encoding="utf-8")


def _venv_python() -> Path:
    script_dir = "Scripts" if os.name == "nt" else "bin"
    python_name = "python.exe" if os.name == "nt" else "python"
    return VENV_DIR / script_dir / python_name


def _ensure_virtualenv(python_executable: str) -> None:
    if VENV_DIR.exists():
        return
    _log(f"Creating virtual environment at {VENV_DIR}")
    subprocess.check_call([python_executable, "-m", "venv", str(VENV_DIR)])


def _install_requirements(python_executable: Path) -> None:
    _log("Installing Firebase function requirements")

    upgrade_cmd = [str(python_executable), "-m", "pip", "install", "--upgrade", "pip"]
    try:
        subprocess.check_call(upgrade_cmd)
    except subprocess.CalledProcessError as exc:
        _log(
            "pip upgrade failed with exit code "
            f"{exc.returncode}; continuing without upgrading pip"
        )

    subprocess.check_call(
        [str(python_executable), "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)]
    )


def ensure() -> None:
    """Main entry point invoked by ``python -m functions.devtools.ensure_venv``."""

    if not REQUIREMENTS_PATH.exists():
        raise EnsureVenvError(
            f"Could not find requirements file at {REQUIREMENTS_PATH}."
        )

    python_executable = sys.executable
    _log(f"Using Python interpreter: {python_executable}")

    _ensure_virtualenv(python_executable)

    requirements_hash = _hash_requirements(REQUIREMENTS_PATH)
    venv_python = _venv_python()

    if not venv_python.exists():
        raise EnsureVenvError(
            "Virtualenv created but python executable missing at "
            f"{venv_python}."
        )

    if _should_install(requirements_hash):
        _install_requirements(venv_python)
        _write_marker(requirements_hash)
    else:
        _log("Dependencies already satisfied; skipping install")

    _log("Firebase virtual environment is ready")


if __name__ == "__main__":  # pragma: no cover - manual execution path
    try:
        ensure()
    except EnsureVenvError as exc:
        _log(str(exc))
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        _log(f"Command failed with exit code {exc.returncode}")
        sys.exit(exc.returncode)
