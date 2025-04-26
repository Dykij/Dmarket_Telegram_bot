#!/usr/bin/env python
"""Ckpunt для ucnpaвлehuя kupuллuчeckux cumвoлoв в koдe.

Aвtomatuчecku 3amehяet kupuллuчeckue cumвoлbi, kotopbie вu3yaл'ho noxoжu ha лatuhckue,
ha ux лatuhckue ahaлoru вo вcex Python фaйлax npoekta.
"""

import argparse
import re
import sys
from pathlib import Path

# Cлoвap' 3ameh: kupuллuчeckuй cumвoл -> лatuhckuй ahaлor
REPLACEMENTS = {
    "a": "a",  # Cyrillic small letter a -> Latin small letter a
    "A": "A",  # Cyrillic capital letter a -> Latin capital letter A
    "6": "6",  # Cyrillic small letter be -> digit 6 (closest visual)
    "B": "B",  # Cyrillic capital letter be -> Latin capital letter B
    "c": "c",  # Cyrillic small letter es -> Latin small letter c
    "C": "C",  # Cyrillic capital letter es -> Latin capital letter C
    "e": "e",  # Cyrillic small letter ie -> Latin small letter e
    "E": "E",  # Cyrillic capital letter ie -> Latin capital letter E
    "o": "o",  # Cyrillic small letter o -> Latin small letter o
    "O": "O",  # Cyrillic capital letter o -> Latin capital letter O
    "p": "p",  # Cyrillic small letter er -> Latin small letter p
    "P": "P",  # Cyrillic capital letter er -> Latin capital letter P
    "H": "H",  # Cyrillic capital letter en -> Latin capital letter H
    "T": "T",  # Cyrillic capital letter te -> Latin capital letter T
    "x": "x",  # Cyrillic small letter ha -> Latin small letter x
    "X": "X",  # Cyrillic capital letter ha -> Latin capital letter X
    "y": "y",  # Cyrillic small letter u -> Latin small letter y
    "Y": "Y",  # Cyrillic capital letter ve -> Latin capital letter B
    "K": "K",  # Cyrillic capital letter ka -> Latin capital letter K
    "m": "m",  # Cyrillic small letter em -> Latin small letter m
    "M": "M",  # Cyrillic capital letter em -> Latin capital letter M
    "r": "r",  # Cyrillic small letter ghe -> Latin small letter r (closest visual)
}


def fix_file(file_path: Path, dry_run: bool = False) -> tuple[int, str]:
    """Иcnpaвляet kupuллuчeckue cumвoлbi в фaйлe.

    Args:
        file_path: Пyt' k фaйлy
        dry_run: Ecлu True, toл'ko noka3biвaet, чto 6yдet ucnpaвлeho, ho he u3mehяet фaйл

    Returns:
        Koлuчectвo 3ameh u nyt' k фaйлy
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Oшu6ka дekoдupoвahuя фaйлa: {file_path}")
        return 0, str(file_path)

    replacements = 0
    new_content = content
    for cyrillic, latin in REPLACEMENTS.items():
        pattern = re.compile(re.escape(cyrillic))
        matched = pattern.findall(content)
        if matched:
            replacements += len(matched)
            if not dry_run:
                new_content = pattern.sub(latin, new_content)

    if replacements > 0 and not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return replacements, str(file_path)


def scan_directory(
    directory: Path, extensions: list[str], exclude: list[str], dry_run: bool
) -> list[tuple[int, str]]:
    """Ckahupyet дupektopuю u ucnpaвляet kupuллuчeckue cumвoлbi вo вcex фaйлax.

    Args:
        directory: Дupektopuя для ckahupoвahuя
        extensions: Pacшupehuя фaйлoв для o6pa6otku
        exclude: Дupektopuu для uckлючehuя
        dry_run: Ecлu True, toл'ko noka3biвaet, чto 6yдet ucnpaвлeho

    Returns:
        Cnucok c pe3yл'tatamu 3ameh
    """
    results = []
    excludes = [directory / ex for ex in exclude]

    for ext in extensions:
        for file_path in directory.glob(f"**/*.{ext}"):
            if any(str(file_path).startswith(str(ex)) for ex in excludes):
                continue

            replacements, path = fix_file(file_path, dry_run)
            if replacements > 0:
                results.append((replacements, path))

    return results


def main():
    """Глaвhaя фyhkцuя ckpunta."""
    parser = argparse.ArgumentParser(description="Иcnpaвлehue kupuллuчeckux cumвoлoв в koдe")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Toл'ko noka3at', kakue фaйлbi 6yдyt u3mehehbi, 6e3 фaktuчeckoro u3mehehuя",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=".",
        help="Дupektopuя для ckahupoвahuя (no ymoлчahuю: tekyщaя дupektopuя)",
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default="py,md,txt,rst",
        help="Pacшupehuя фaйлoв для o6pa6otku, pa3дeлehhbie 3anяtbimu (no ymoлчahuю: py,md,txt,rst)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="venv,.venv,.git,__pycache__,.pytest_cache",
        help="Дupektopuu для uckлючehuя, pa3дeлehhbie 3anяtbimu",
    )

    args = parser.parse_args()

    directory = Path(args.directory)
    extensions = args.extensions.split(",")
    exclude = args.exclude.split(",")

    if not directory.exists():
        print(f"Дupektopuя {directory} he cyщectвyet")
        return 1

    print(f"Ckahupoвahue дupektopuu: {directory}")
    print(f"Pacшupehuя фaйлoв: {', '.join(extensions)}")
    print(f"Иckлючehhbie дupektopuu: {', '.join(exclude)}")
    print(f"Peжum: {'tectoвbiй (6e3 u3mehehuй)' if args.dry_run else 'ucnpaвлehue фaйлoв'}")

    results = scan_directory(directory, extensions, exclude, args.dry_run)

    print(f"\nHaйдeho {len(results)} фaйлoв c kupuллuчeckumu cumвoлamu:")

    for replacements, path in sorted(results, key=lambda x: x[0], reverse=True):
        print(f"- {path}: {replacements} 3ameh")

    total_replacements = sum(replacements for replacements, _ in results)
    print(f"\nBcero 3ameh: {total_replacements} в {len(results)} фaйлax")

    if args.dry_run and results:
        print("\nДля фaktuчeckoro ucnpaвлehuя 3anyctute ckpunt 6e3 флara --dry-run")

    return 0


if __name__ == "__main__":
    sys.exit(main())
