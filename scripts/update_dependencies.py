#!/usr/bin/env python
"""Script to update Poetry dependencies.

This script helps upgrade project dependencies to their latest versions.
"""

import subprocess
import sys
from typing import List


def run_command(command: List[str], description: str) -> None:
    """Run a shell command and print its output."""
    print(f"\n🚀 {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def update_dependencies(args: List[str]) -> None:
    """Update Poetry dependencies based on command line arguments."""
    # Install Poetry if not already installed
    if not run_command(["poetry", "--version"], "Checking Poetry installation"):
        print("Installing Poetry...")
        subprocess.run(
            "curl -sSL https://install.python-poetry.org | python3 -", shell=True, check=False
        )

    # Update Poetry itself
    run_command(["poetry", "self", "update"], "Updating Poetry to the latest version")

    # Check for outdated dependencies
    run_command(["poetry", "show", "--outdated"], "Checking for outdated dependencies")

    # Update dependencies
    if not args or "--all" in args:
        # Update all dependencies
        run_command(["poetry", "update"], "Updating all dependencies")
    else:
        # Update specific dependencies
        packages = [arg for arg in args if not arg.startswith("--")]
        if packages:
            run_command(
                ["poetry", "update"] + packages,
                f"Updating specified dependencies: {', '.join(packages)}",
            )

    # Install dependencies
    run_command(["poetry", "install"], "Installing dependencies")

    # Create a requirements.txt file
    run_command(
        ["poetry", "export", "--format", "requirements.txt", "--output", "requirements.txt"],
        "Generating requirements.txt file",
    )

    print("\n✅ Dependency update completed!")


if __name__ == "__main__":
    update_dependencies(sys.argv[1:])
