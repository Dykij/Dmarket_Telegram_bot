#!/usr/bin/env python
"""Script to make Python files executable.

This script adds appropriate shebang lines and sets executable permissions
(on Unix-like systems) for Python scripts in the project.
"""

import os
import stat
from pathlib import Path

SHEBANG = "#!/usr/bin/env python"
SCRIPT_DIRS = ["scripts"]
SCRIPT_EXTENSIONS = [".py"]


def add_shebang(file_path):
    """Add shebang line to a Python file if it doesn't already have one."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    if not content.startswith(SHEBANG):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{SHEBANG}\n{content}")
        print(f"Added shebang to {file_path}")
    else:
        print(f"Shebang already exists in {file_path}")


def make_executable(file_path):
    """Set executable permission on a file (Unix-like systems only)."""
    if os.name == "posix":  # Unix-like systems
        current_permissions = os.stat(file_path).st_mode
        os.chmod(file_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Set executable permissions on {file_path}")
    else:
        print(f"Skipping permission setting for {file_path} (non-Unix system)")


def process_scripts():
    """Find and process all Python script files."""
    base_dir = Path(__file__).parent.parent

    for script_dir in SCRIPT_DIRS:
        dir_path = base_dir / script_dir
        if not dir_path.exists():
            print(f"Directory {dir_path} does not exist, creating it...")
            dir_path.mkdir(parents=True, exist_ok=True)

        print(f"Processing scripts in {dir_path}...")

        for file_path in dir_path.glob("**/*"):
            if file_path.is_file() and file_path.suffix in SCRIPT_EXTENSIONS:
                print(f"Processing {file_path}")
                add_shebang(file_path)
                make_executable(file_path)

    print("Processing complete!")


if __name__ == "__main__":
    process_scripts()
