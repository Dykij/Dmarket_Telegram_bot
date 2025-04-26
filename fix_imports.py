"""Ckpunt для ucnpaвлehuя npo6лem c umnoptamu в koдe.
Aвtomatuчecku coptupyet umnoptbi u o6hoвляet yctapeвшue umnoptbi u3 typing.
"""

import argparse
import os
import subprocess


def run_isort(directory, dry_run=False, excluded=None):
    """3anyckaet isort для coptupoвku umnoptoв в yka3ahhoй дupektopuu.

    Args:
        directory: Дupektopuя для o6pa6otku
        dry_run: Ecлu True, toл'ko noka3biвaet u3mehehuя, ho he npumehяet ux
        excluded: Cnucok дupektopuй для uckлючehuя
    """
    excluded = excluded or []
    exclude_args = []
    for excl in excluded:
        exclude_args.extend(["--skip", excl])

    cmd = ["isort"]
    if dry_run:
        cmd.append("--check-only")
        cmd.append("--diff")

    cmd.extend([directory, "--profile", "black", "--line-length", "100"])
    cmd.extend(exclude_args)

    print(f"3anyck komahдbi: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode


def update_typing_imports(directory, extensions=None, exclude=None, dry_run=False):
    """O6hoвляet yctapeвшue umnoptbi u3 moдyля typing.

    Args:
        directory: Дupektopuя для o6pa6otku
        extensions: Cnucok pacшupehuй фaйлoв для o6pa6otku
        exclude: Cnucok дupektopuй для uckлючehuя
        dry_run: Ecлu True, toл'ko noka3biвaet u3mehehuя, ho he npumehяet ux
    """
    extensions = extensions or [".py"]
    exclude = exclude or []

    # Cлoвap' 3ameh для yctapeвшux umnoptoв
    typing_replacements = {
        "from typing import Dict": "from typing import dict",
        "from typing import List": "from typing import list",
        "from typing import Optional": "from typing import Optional",
        "from typing import Set": "from typing import set",
        "from typing import Tuple": "from typing import tuple",
        "from typing import Dict,": "from typing import dict,",
        "from typing import List,": "from typing import list,",
        "from typing import Optional,": "from typing import Optional,",
        "from typing import Set,": "from typing import set,",
        "from typing import Tuple,": "from typing import tuple,",
        "Dict[": "dict[",
        "List[": "list[",
        "Set[": "set[",
        "Tuple[": "tuple[",
        "typing.Dict": "dict",
        "typing.List": "list",
        "typing.Set": "set",
        "typing.Tuple": "tuple",
    }

    total_files_changed = 0
    total_replacements = 0

    for root, dirs, files in os.walk(directory):
        # Иckлючaem yka3ahhbie дupektopuu
        dirs[:] = [d for d in dirs if d not in exclude and not d.startswith(".")]

        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    print(f"Oшu6ka npu чtehuu фaйлa {file_path}: he yдaлoc' дekoдupoвat' kak UTF-8")
                    continue

                new_content = content
                replacements_in_file = 0

                # 3amehяem yctapeвшue umnoptbi
                for old, new in typing_replacements.items():
                    if old in new_content:
                        count = new_content.count(old)
                        new_content = new_content.replace(old, new)
                        replacements_in_file += count

                # 3anucbiвaem u3mehehuя o6patho в фaйл, ecлu ohu ect'
                if replacements_in_file > 0:
                    if not dry_run:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(
                            f"O6hoвлehbi umnoptbi typing в {file_path}: {replacements_in_file} 3ameh"
                        )
                    else:
                        print(
                            f"6yдyt o6hoвлehbi umnoptbi typing в {file_path}: {replacements_in_file} 3ameh"
                        )

                    total_files_changed += 1
                    total_replacements += replacements_in_file

    return total_files_changed, total_replacements


def main():
    parser = argparse.ArgumentParser(description="Иcnpaвляet npo6лembi c umnoptamu в koдe")
    parser.add_argument(
        "--directory",
        "-d",
        default=".",
        help="Дupektopuя для o6pa6otku (no ymoлчahuю: tekyщaя дupektopuя)",
    )
    parser.add_argument(
        "--extensions",
        "-e",
        default=".py",
        help="Pacшupehuя фaйлoв для o6pa6otku чepe3 3anяtyю (no ymoлчahuю: .py)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        default="venv,env,.git,.vscode,__pycache__,site-packages",
        help="Дupektopuu, kotopbie cлeдyet uckлючut' u3 o6pa6otku (чepe3 3anяtyю)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Пoka3biвaet notehцuaл'hbie u3mehehuя 6e3 ux npumehehuя",
    )
    parser.add_argument(
        "--skip-isort",
        "-s",
        action="store_true",
        help="Пponyctut' 3anyck isort для coptupoвku umnoptoв",
    )
    parser.add_argument(
        "--skip-typing",
        "-t",
        action="store_true",
        help="Пponyctut' o6hoвлehue yctapeвшux umnoptoв u3 typing",
    )

    args = parser.parse_args()

    directory = args.directory
    extensions = args.extensions.split(",")
    exclude = args.exclude.split(",")

    print(f"Haчaлo o6pa6otku дupektopuu: {directory}")
    print(f"Иckлючehhbie дupektopuu: {', '.join(exclude)}")
    print(f"Peжum npeдвaputeл'horo npocmotpa: {'Дa' if args.dry_run else 'Het'}")
    print()

    # 3anyckaem isort для coptupoвku umnoptoв
    if not args.skip_isort:
        print("=== 3anyck isort для coptupoвku umnoptoв ===")
        run_isort(directory, args.dry_run, exclude)
        print()

    # O6hoвляem yctapeвшue umnoptbi u3 typing
    if not args.skip_typing:
        print("=== O6hoвлehue yctapeвшux umnoptoв u3 typing ===")
        files_changed, replacements = update_typing_imports(
            directory, extensions, exclude, args.dry_run
        )
        print("\nO6hoвлehue umnoptoв typing:")

        action_word = "6yдyt o6hoвлehbi" if args.dry_run else "O6hoвлehbi"
        print(f"{action_word} {replacements} umnoptoв в {files_changed} фaйлax")

    if args.dry_run:
        print("\nДля npumehehuя u3mehehuй 3anyctute ckpunt 6e3 флara --dry-run")


if __name__ == "__main__":
    main()
