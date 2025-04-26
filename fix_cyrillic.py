"""Скрипт для исправления проблем с кириллическими символами в коде.

Заменяет русские буквы, похожие на латинские, на правильные латинские символы.
"""

import argparse
import logging
import os
import re
from pathlib import Path

# Максимальное количество примеров для отображения
MAX_EXAMPLES = 3

# Словарь замен кириллических символов на латинские
CYRILLIC_TO_LATIN = {
    # Кириллические буквы, которые выглядят как латинские
    "А": "A",  # Кириллическая A -> Латинская A
    "В": "B",  # Кириллическая В -> Латинская B
    "Е": "E",  # Кириллическая Е -> Латинская E
    "К": "K",  # Кириллическая К -> Латинская K
    "М": "M",  # Кириллическая М -> Латинская M
    "Н": "H",  # Кириллическая Н -> Латинская H
    "О": "O",  # Кириллическая О -> Латинская O
    "Р": "P",  # Кириллическая Р -> Латинская P
    "С": "C",  # Кириллическая С -> Латинская C
    "Т": "T",  # Кириллическая Т -> Латинская T
    "Х": "X",  # Кириллическая Х -> Латинская X
    "а": "a",  # Кириллическая а -> Латинская a
    "е": "e",  # Кириллическая е -> Латинская e
    "о": "o",  # Кириллическая о -> Латинская o
    "р": "p",  # Кириллическая р -> Латинская p
    "с": "c",  # Кириллическая с -> Латинская c
    "у": "y",  # Кириллическая у -> Латинская y
    "х": "x",  # Кириллическая х -> Латинская x
    # Специфические замены, часто встречающиеся в коде
    "З": "3",  # Кириллическая З -> цифра 3 (частая ошибка в коде)
    "з": "3",  # Кириллическая з -> цифра 3
    "б": "6",  # Кириллическая б -> цифра 6
    "Б": "6",  # Кириллическая Б -> цифра 6
}

# Паттерны для поиска закомментированного кода
COMMENTED_CODE_PATTERNS = [
    r"# .*[=+\-*/\[\]\{\}()].*",  # Операторы и скобки в комментариях
    r"#\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*\)",  # Вызовы функций в комментариях
    r"#\s*(from|import)\s+[a-zA-Z_]",  # Импорты в комментариях
    r"#\s*(class|def|if|else|for|while|try|except|with)\s+",  # Ключевые слова в комментариях
]


def fix_file(file_path, dry_run=False):
    """Исправляет проблемы с кириллическими символами в указанном файле.

    Args:
        file_path: Путь к файлу для исправления
        dry_run: Если True, только показывает изменения, но не применяет их

    Returns:
        tuple: (количество замен, количество предупреждений)
    """
    try:
        file_path = Path(file_path)
        with file_path.open(encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        logging.error(f"Ошибка при чтении файла {file_path}: не удалось декодировать как UTF-8")
        return 0, 1

    replacements = 0
    warnings = 0

    # Заменяем кириллические символы на латинские
    new_content = content
    for cyrillic, latin in CYRILLIC_TO_LATIN.items():
        if cyrillic in content:
            count = content.count(cyrillic)
            new_content = new_content.replace(cyrillic, latin)
            replacements += count

    # Проверяем закомментированный код
    for pattern in COMMENTED_CODE_PATTERNS:
        matches = re.findall(pattern, new_content)
        if matches:
            warnings += len(matches)
            if dry_run:
                logging.warning(f"Предупреждение: возможно закомментированный код в {file_path}:")
                for match in matches[:MAX_EXAMPLES]:  # Показываем первые MAX_EXAMPLES совпадения
                    logging.info(f"  {match.strip()}")
                if len(matches) > MAX_EXAMPLES:
                    logging.info(f"  ... и еще {len(matches) - MAX_EXAMPLES}")

    if replacements > 0 and not dry_run:
        with file_path.open("w", encoding="utf-8") as f:
            f.write(new_content)

    return replacements, warnings


def process_directory(directory, extensions, exclude=None, dry_run=False):
    """Обрабатывает все файлы в директории с указанными расширениями.

    Args:
        directory: Директория для обработки
        extensions: Список расширений файлов для обработки
        exclude: Список директорий для исключения
        dry_run: Если True, только показывает изменения, но не применяет их

    Returns:
        tuple: (общее количество замен, количество измененных файлов, количество предупреждений)
    """
    if exclude is None:
        exclude = []

    total_replacements = 0
    total_warnings = 0
    changed_files = 0

    for root, dirs, files in os.walk(directory):
        # Исключаем указанные директории
        dirs[:] = [d for d in dirs if d not in exclude]

        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = Path(root) / file
                replacements, warnings = fix_file(file_path, dry_run)
                total_warnings += warnings

                if replacements > 0:
                    changed_files += 1
                    total_replacements += replacements
                    if dry_run:
                        logging.info(f"В файле {file_path} будет заменено {replacements} символов")
                    else:
                        logging.info(
                            f"Исправлен файл {file_path}: заменено {replacements} символов"
                        )

    return total_replacements, changed_files, total_warnings


def main():
    """Основная функция скрипта для исправления кириллических символов в коде.
    Разбирает аргументы командной строки и запускает обработку файлов.
    """
    parser = argparse.ArgumentParser(
        description="Исправляет проблемы с кириллическими символами в коде"
    )
    parser.add_argument(
        "-d", "--directory", default=".", help="Директория для обработки (по умолчанию: текущая)"
    )
    parser.add_argument(
        "-e",
        "--extensions",
        default=".py,.pyx,.pyi",
        help="Расширения файлов для обработки (через запятую, по умолчанию: .py,.pyx,.pyi)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        default="venv,.venv,.git,__pycache__,build,dist",
        help="Директории для исключения (через запятую)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать, какие изменения будут сделаны, но не применять их",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Показывать подробную информацию"
    )
    args = parser.parse_args()

    # Настраиваем логирование
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    extensions = args.extensions.split(",")
    exclude = args.exclude.split(",")

    logging.info(f"Начало обработки директории: {args.directory}")
    logging.info(f"Расширения файлов: {', '.join(extensions)}")
    logging.info(f"Исключенные директории: {', '.join(exclude)}")
    logging.info(f"Режим предварительного просмотра: {'Да' if args.dry_run else 'Нет'}")
    logging.info("")

    total_replacements, changed_files, total_warnings = process_directory(
        args.directory, extensions, exclude, args.dry_run
    )

    logging.info("\nЗавершено!")
    action_word = "Будет заменено" if args.dry_run else "Заменено"
    logging.info(f"{action_word} {total_replacements} символов в {changed_files} файлах")
    logging.info(f"Обнаружено {total_warnings} предупреждений о закомментированном коде")

    if args.dry_run and total_replacements > 0:
        logging.info("\nДля применения изменений запустите скрипт без флага --dry-run")


if __name__ == "__main__":
    main()
