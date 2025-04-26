#!/usr/bin/env python
"""Project initialization script.

This script sets up the project environment, installs dependencies,
and configures the necessary components to get started.
"""

import os
import subprocess
import sys
from pathlib import Path


def print_section(title):
    """Print a section title."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def run_command(command, description=None):
    """Run a shell command."""
    if description:
        print(f"\n> {description}")

    print(f"$ {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing '{command}':")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def setup_environment():
    """Set up the project environment."""
    print_section("Setting up environment")

    # Check if Poetry is installed
    poetry_installed = run_command("poetry --version", "Checking if Poetry is installed")

    if not poetry_installed:
        print("Installing Poetry...")
        if not run_command(
            "curl -sSL https://install.python-poetry.org | python3 -", "Installing Poetry"
        ):
            print("Failed to install Poetry. Please install it manually.")
            return False

    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        print("Creating .env file from example.env")
        example_env = Path("example.env")
        if example_env.exists():
            with open(example_env) as src, open(env_file, "w") as dest:
                dest.write(src.read())
            print(".env file created. Please update it with your settings.")
        else:
            print("example.env not found. Please create a .env file manually.")

    # Create directories
    print("Creating required directories...")
    os.makedirs("logs", exist_ok=True)
    os.makedirs("utils_mount", exist_ok=True)

    # Create empty proxies file if it doesn't exist
    proxies_file = Path("utils_mount/dmarket_proxies.txt")
    if not proxies_file.exists():
        proxies_file.touch()
        print("Created empty proxies file at utils_mount/dmarket_proxies.txt")

    return True


def install_dependencies():
    """Install project dependencies using Poetry."""
    print_section("Installing dependencies")

    # Install dependencies
    if not run_command("poetry install", "Installing dependencies"):
        return False

    # Check for available updates
    run_command("poetry show --outdated", "Checking for outdated dependencies")

    return True


def run_checks():
    """Run basic checks to verify the installation."""
    print_section("Running checks")

    # Verify the installation
    checks = [
        ("poetry check", "Poetry project validation"),
        (
            "poetry run python -c \"import price_monitoring; print('Price monitoring module found!')\"",
            "Import check",
        ),
    ]

    all_passed = True
    for cmd, desc in checks:
        if not run_command(cmd, desc):
            all_passed = False

    return all_passed


def main():
    """Main function to initialize the project."""
    print("\n🚀 Initializing DMarket Price Monitoring Bot project\n")

    steps = [
        ("Setting up environment", setup_environment),
        ("Installing dependencies", install_dependencies),
        ("Running checks", run_checks),
    ]

    step_results = {}

    for step_name, step_func in steps:
        if all(step_results.values()):  # Only continue if all previous steps succeeded
            print(f"\n>> {step_name}...")
            step_results[step_name] = step_func()
        else:
            step_results[step_name] = False

    print_section("Initialization Summary")

    all_successful = all(step_results.values())

    for step_name, result in step_results.items():
        status = "✅ Success" if result else "❌ Failed"
        print(f"{status} - {step_name}")

    if all_successful:
        print("\n🎉 Project successfully initialized!")
        print("\nNext steps:")
        print("  1. Edit your .env file with appropriate values")
        print("  2. Run 'poetry run start' to start the bot")
        print("  3. Run 'poetry run worker' to start the worker process")
        print("\nHappy coding! 🚀")
        return 0
    else:
        print("\n❌ Project initialization had some issues.")
        print("Please fix the errors and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
