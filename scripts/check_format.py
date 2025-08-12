#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if code formatting is correct without making changes
"""
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return True if successful"""
    print(f"Checking {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Issues found with {description}:")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def main():
    """Check code formatting without making changes"""
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

    # Check isort
    if not run_command(
        [uv_path, "run", "isort", "--check-only", "."], "import sorting"
    ):
        success = False

    # Check black
    if not run_command([uv_path, "run", "black", "--check", "."], "code formatting"):
        success = False

    if success:
        print("Code formatting is correct!")
    else:
        print(
            "Code formatting issues found! Run 'uv run python scripts/format.py' to fix."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
