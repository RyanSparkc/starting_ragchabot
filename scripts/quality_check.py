#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive code quality check script
"""
import subprocess
import sys
from pathlib import Path


def run_script(script_name: str) -> bool:
    """Run a Python script and return True if successful"""
    script_path = Path(__file__).parent / script_name
    try:
        result = subprocess.run([sys.executable, str(script_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Run all code quality checks"""
    print("Running comprehensive code quality checks...\n")

    success = True

    # Run formatting
    print("=" * 50)
    print("FORMATTING")
    print("=" * 50)
    if not run_script("format.py"):
        success = False

    print("\n")

    # Run linting
    print("=" * 50)
    print("LINTING")
    print("=" * 50)
    if not run_script("lint.py"):
        success = False

    print("\n")
    print("=" * 50)

    if success:
        print("All code quality checks passed!")
    else:
        print("Some code quality checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
