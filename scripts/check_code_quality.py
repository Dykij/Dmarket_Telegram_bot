#!/usr/bin/env python
"""Code Quality Check Script.

This script runs various code quality tools and helps fix common issues.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Configuration
CHECK_DIRS = ["price_monitoring", "common", "tests", "scripts"]
EXCLUDE_DIRS = ["__pycache__", ".venv", "venv", ".git", ".mypy_cache", ".ruff_cache"]


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{BOLD}{'=' * 80}{RESET}")
    print(f"{BOLD}{title.center(80)}{RESET}")
    print(f"{BOLD}{'=' * 80}{RESET}\n")


def run_command(command: List[str], description: str) -> Tuple[bool, Optional[str]]:
    """Run a command and return success status and output."""
    print(f"{YELLOW}>> {description}...{RESET}")
    print(f"$ {' '.join(command)}")

    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{GREEN}✓ Success!{RESET}")
            return True, result.stdout
        else:
            print(f"{RED}✗ Failed with exit code {result.returncode}{RESET}")
            return False, result.stderr
    except Exception as e:
        print(f"{RED}✗ Error: {e!s}{RESET}")
        return False, str(e)


def check_ruff() -> bool:
    """Run Ruff linter to check for errors."""
    print_header("Running Ruff Linter")
    success, output = run_command(
        ["poetry", "run", "ruff", "check", "."], "Checking code with Ruff"
    )

    if not success and output:
        print("\nIssues found:")
        print(output)

        print(f"\n{YELLOW}Attempting to fix auto-fixable issues...{RESET}")
        fix_success, fix_output = run_command(
            ["poetry", "run", "ruff", "check", "--fix", "."], "Auto-fixing Ruff issues"
        )

        if fix_success:
            print(f"{GREEN}Successfully fixed some Ruff issues!{RESET}")
        else:
            print(f"{RED}Some issues could not be automatically fixed.{RESET}")
            if fix_output:
                print("\nRemaining issues:")
                print(fix_output)

    return success


def check_black() -> bool:
    """Check code formatting with Black."""
    print_header("Checking Code Formatting with Black")

    # First check if formatting is needed
    check_success, check_output = run_command(
        ["poetry", "run", "black", "--check", "."], "Checking if code needs formatting with Black"
    )

    if not check_success:
        print(f"\n{YELLOW}Code needs formatting. Applying Black...{RESET}")
        format_success, format_output = run_command(
            ["poetry", "run", "black", "."], "Formatting code with Black"
        )

        if format_success:
            print(f"{GREEN}Successfully formatted code with Black!{RESET}")
            return True
        else:
            print(f"{RED}Failed to format some files with Black.{RESET}")
            if format_output:
                print("\nErrors:")
                print(format_output)
            return False

    return True


def check_mypy() -> bool:
    """Run MyPy for type checking."""
    print_header("Running MyPy Type Checker")

    success, output = run_command(["poetry", "run", "mypy", "."], "Checking types with MyPy")

    if not success and output:
        print("\nType issues found:")
        print(output)
        print(f"\n{YELLOW}Note: Type issues must be fixed manually.{RESET}")

    return success


def check_pylint() -> bool:
    """Run Pylint for deep code analysis."""
    print_header("Running Pylint Code Analysis")

    # Check each directory separately to get more focused feedback
    overall_success = True

    for directory in CHECK_DIRS:
        if not os.path.exists(directory):
            continue

        print(f"\n{YELLOW}Checking {directory}...{RESET}")
        success, output = run_command(
            ["poetry", "run", "pylint", directory], f"Running Pylint on {directory}"
        )

        if not success:
            overall_success = False
            if output:
                print("\nIssues found:")
                print(output)

    if not overall_success:
        print(f"\n{YELLOW}Note: Pylint issues must be fixed manually.{RESET}")

    return overall_success


def find_unused_imports() -> bool:
    """Find unused imports using autoflake."""
    print_header("Finding Unused Imports")

    success, output = run_command(
        [
            "poetry",
            "run",
            "autoflake",
            "--remove-all-unused-imports",
            "--recursive",
            "--exclude",
            ",".join(EXCLUDE_DIRS),
            "--check",
            ".",
        ],
        "Checking for unused imports with autoflake",
    )

    if not success and output:
        print("\nUnused imports found:")
        print(output)

        response = input(f"{YELLOW}Do you want to remove unused imports? (y/n): {RESET}")
        if response.lower() == "y":
            remove_success, remove_output = run_command(
                [
                    "poetry",
                    "run",
                    "autoflake",
                    "--remove-all-unused-imports",
                    "--recursive",
                    "--exclude",
                    ",".join(EXCLUDE_DIRS),
                    "--in-place",
                    ".",
                ],
                "Removing unused imports",
            )

            if remove_success:
                print(f"{GREEN}Successfully removed unused imports!{RESET}")
                return True
            else:
                print(f"{RED}Failed to remove some unused imports.{RESET}")
                return False

    return True


def check_import_errors() -> bool:
    """Check for import errors by attempting to import each module."""
    print_header("Checking for Import Errors")

    # Create a simple script to try importing all modules
    import_check_script = f"""
import importlib
import os
import sys
from pathlib import Path

def check_imports(directory):
    errors = []
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in {EXCLUDE_DIRS!r}]
        
        for file in files:
            if file.endswith('.py'):
                # Convert file path to module name
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path)
                module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
                
                # Skip __init__.py when the module name would be just the directory
                if file == '__init__.py' and module_name.endswith('__init__'):
                    module_name = module_name[:-9]
                    
                try:
                    print(f"Trying to import {{module_name}}...", end='')
                    importlib.import_module(module_name)
                    print(" Success")
                except (ImportError, ModuleNotFoundError) as e:
                    errors.append((module_name, str(e)))
                    print(f" Failed: {{e}}")
                except Exception as e:
                    errors.append((module_name, f"Unexpected error: {{str(e)}}"))
                    print(f" Error: {{e}}")
    
    return errors

if __name__ == "__main__":
    errors = []
    for directory in {CHECK_DIRS!r}:
        if os.path.exists(directory):
            print(f"\\nChecking imports in {{directory}}...")
            dir_errors = check_imports(directory)
            errors.extend(dir_errors)
    
    if errors:
        print("\\nImport errors found:")
        for module, error in errors:
            print(f"  - {{module}}: {{error}}")
        sys.exit(1)
    else:
        print("\\nNo import errors found.")
        sys.exit(0)
"""

    # Save to temporary file
    temp_file = Path("_temp_import_check.py")
    try:
        with open(temp_file, "w") as f:
            f.write(import_check_script)

        # Run the script
        success, output = run_command(
            ["poetry", "run", "python", str(temp_file)], "Checking for import errors"
        )

        if not success and output:
            print("\nImport errors found:")
            print(output)
            print(f"\n{YELLOW}Note: Import errors must be fixed manually.{RESET}")

        return success
    finally:
        if temp_file.exists():
            temp_file.unlink()


def main() -> int:
    """Run all code quality checks."""
    print_header("DMarket Bot - Code Quality Check")

    checks = [
        ("Black Formatting", check_black),
        ("Ruff Linting", check_ruff),
        ("Import Errors", check_import_errors),
        ("Unused Imports", find_unused_imports),
        ("MyPy Type Checking", check_mypy),
        ("Pylint Deep Analysis", check_pylint),
    ]

    results = {}

    for name, check_func in checks:
        print(f"\n{BOLD}{name}{RESET}")
        try:
            result = check_func()
            results[name] = result
        except Exception as e:
            print(f"{RED}Error running {name}: {e!s}{RESET}")
            results[name] = False

    # Print summary
    print_header("Summary")

    all_passed = True
    for name, result in results.items():
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"{name}: {status}")
        if not result:
            all_passed = False

    if all_passed:
        print(f"\n{GREEN}All checks passed! 🎉{RESET}")
        return 0
    else:
        print(f"\n{YELLOW}Some checks failed. See above for details.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
