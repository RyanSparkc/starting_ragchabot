#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code linting script using flake8 and mypy
"""
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return True if successful"""
    print(f"Running {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {description}:")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def main():
    """Run linting checks"""
    project_root = Path(__file__).parent.parent

    # Change to project root
    import os

    os.chdir(project_root)

    # Detect uv path
    uv_path = "uv"
    if sys.platform == "win32":
        import shutil

        uv_exe = shutil.which("uv")
        if not uv_exe:
            # Try common Windows location
            potential_path = Path.home() / ".local" / "bin" / "uv.exe"
            if potential_path.exists():
                uv_path = str(potential_path)

    success = True

    # Run flake8
    flake8_cmd = [
        uv_path,
        "run",
        "flake8",
        "--max-line-length=88",
        "--extend-ignore=E203,W503",  # Ignore conflicts with black
        "backend/",
        "main.py",
        "scripts/",
    ]
    if not run_command(flake8_cmd, "flake8 (code linting)"):
        success = False

    # Run mypy (with less strict settings for now)
    mypy_cmd = [
        uv_path,
        "run",
        "mypy",
        "--ignore-missing-imports",
        "--no-strict-optional",
        "backend/",
        "main.py",
    ]
    if not run_command(mypy_cmd, "mypy (type checking)"):
        success = False

    if success:
        print("Linting completed successfully!")
    else:
        print("Linting found issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()
