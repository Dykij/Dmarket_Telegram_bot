#!/usr/bin/env python
"""Script for fixing issues with Cyrillic characters in code.

Replaces Russian letters that look like Latin ones with proper Latin characters.
"""

import argparse
import logging
import os
import re
from pathlib import Path

# Maximum number of examples to display
MAX_EXAMPLES = 3

# Dictionary of Cyrillic to Latin character replacements
CYRILLIC_TO_LATIN = {
    # Cyrillic letters that look like Latin ones
    "А": "A",  # Cyrillic A -> Latin A
    "В": "B",  # Cyrillic B -> Latin B
    "Е": "E",  # Cyrillic E -> Latin E
    "К": "K",  # Cyrillic K -> Latin K
    "М": "M",  # Cyrillic M -> Latin M
    "Н": "H",  # Cyrillic H -> Latin H
    "О": "O",  # Cyrillic O -> Latin O
    "Р": "P",  # Cyrillic P -> Latin P
    "С": "C",  # Cyrillic C -> Latin C
    "Т": "T",  # Cyrillic T -> Latin T
    "Х": "X",  # Cyrillic X -> Latin X
    "а": "a",  # Cyrillic a -> Latin a
    "е": "e",  # Cyrillic e -> Latin e
    "о": "o",  # Cyrillic o -> Latin o
    "р": "p",  # Cyrillic p -> Latin p
    "с": "c",  # Cyrillic c -> Latin c
    "у": "y",  # Cyrillic y -> Latin y
    "х": "x",  # Cyrillic x -> Latin x
    # Specific replacements often found in code
    "З": "3",  # Cyrillic Z -> digit 3 (common error in code)
    "з": "3",  # Cyrillic z -> digit 3
    "б": "6",  # Cyrillic b -> digit 6
    "Б": "6",  # Cyrillic B -> digit 6
    # Additional characters
    "г": "r",  # Cyrillic г -> Latin r
    "и": "u",  # Cyrillic и -> Latin u
    "м": "m",  # Cyrillic м -> Latin m
    "н": "h",  # Cyrillic н -> Latin h
    "к": "k",  # Cyrillic к -> Latin k
    "т": "t",  # Cyrillic т -> Latin t
    "п": "n",  # Cyrillic п -> Latin n (this one is tricky)
    "ы": "bi",  # Cyrillic ы -> Latin bi
    "ь": "'",  # Cyrillic soft sign -> apostrophe
}

# Patterns for finding commented-out code
COMMENTED_CODE_PATTERNS = [
    r"# .*[=+\-*/\[\]\{\}()].*",  # Operators and brackets in comments
    r"#\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*\)",  # Function calls in comments
    r"#\s*(from|import)\s+[a-zA-Z_]",  # Imports in comments
    r"#\s*(class|def|if|else|for|while|try|except|with)\s+",  # Keywords in comments
]


def fix_file(file_path, dry_run=False):
    """Fix Cyrillic character issues in the specified file.

    Args:
        file_path: Path to the file to fix
        dry_run: If True, only shows changes but doesn't apply them

    Returns:
        tuple: (number of replacements, number of warnings)
    """
    try:
        file_path = Path(file_path)
        with file_path.open(encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        logging.error(f"Error reading file {file_path}: could not decode as UTF-8")
        return 0, 1

    replacements = 0
    warnings = 0

    # Replace Cyrillic characters with Latin ones
    new_content = content
    for cyrillic, latin in CYRILLIC_TO_LATIN.items():
        if cyrillic in content:
            count = content.count(cyrillic)
            new_content = new_content.replace(cyrillic, latin)
            replacements += count

    # Check for commented-out code
    for pattern in COMMENTED_CODE_PATTERNS:
        matches = re.findall(pattern, new_content)
        if matches:
            warnings += len(matches)
            if dry_run:
                logging.warning(f"Warning: possible commented-out code in {file_path}:")
                for match in matches[:MAX_EXAMPLES]:  # Show first MAX_EXAMPLES matches
                    logging.info(f"  {match.strip()}")
                if len(matches) > MAX_EXAMPLES:
                    logging.info(f"  ... and {len(matches) - MAX_EXAMPLES} more")

    if replacements > 0 and not dry_run:
        with file_path.open("w", encoding="utf-8") as f:
            f.write(new_content)

    return replacements, warnings


def process_directory(directory, extensions, exclude=None, dry_run=False):
    """Process all files in a directory with specified extensions.

    Args:
        directory: Directory to process
        extensions: List of file extensions to process
        exclude: List of directories to exclude
        dry_run: If True, only shows changes but doesn't apply them

    Returns:
        tuple: (total replacements, number of changed files, number of warnings)
    """
    exclude = exclude or []
    total_replacements = 0
    changed_files = 0
    total_warnings = 0

    directory = Path(directory)

    for root, dirs, files in os.walk(directory):
        # Exclude specified directories
        dirs[:] = [d for d in dirs if d not in exclude and not d.startswith(".")]

        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = Path(root) / file
                replacements, warnings = fix_file(file_path, dry_run)

                total_warnings += warnings
                if replacements > 0:
                    changed_files += 1
                    total_replacements += replacements
                    if dry_run:
                        logging.info(f"Would replace {replacements} characters in {file_path}")
                    else:
                        logging.info(f"Fixed file {file_path}: replaced {replacements} characters")

    return total_replacements, changed_files, total_warnings


def main():
    """Main function for the script to fix Cyrillic characters in code.
    Parses command line arguments and starts file processing.
    """
    parser = argparse.ArgumentParser(description="Fix issues with Cyrillic characters in code")
    parser.add_argument(
        "--directory",
        "-d",
        default=".",
        help="Directory to process (default: current directory)",
    )
    parser.add_argument(
        "--extensions",
        "-e",
        default=".py,.md,.txt,.yaml,.yml,.json",
        help="File extensions to process, comma-separated (default: .py,.md,.txt,.yaml,.yml,.json)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        default="venv,env,.git,.vscode,__pycache__,site-packages",
        help="Directories to exclude from processing (comma-separated)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show potential changes without applying them",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    directory = args.directory
    extensions = args.extensions.split(",")
    exclude = args.exclude.split(",")

    logging.info(f"Starting to process directory: {directory}")
    logging.info(f"File extensions: {', '.join(extensions)}")
    logging.info(f"Excluded directories: {', '.join(exclude)}")
    logging.info(f"Dry run mode: {'Yes' if args.dry_run else 'No'}")
    logging.info("")

    total_replacements, changed_files, total_warnings = process_directory(
        directory, extensions, exclude, args.dry_run
    )

    logging.info("\nCompleted!")

    action_word = "Would replace" if args.dry_run else "Replaced"
    logging.info(f"{action_word} {total_replacements} characters in {changed_files} files")
    logging.info(f"Found {total_warnings} warnings about commented-out code")

    if args.dry_run and total_replacements > 0:
        logging.info("\nTo apply changes, run the script without the --dry-run flag")


if __name__ == "__main__":
    main()
