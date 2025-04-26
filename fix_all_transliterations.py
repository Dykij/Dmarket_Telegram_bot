#!/usr/bin/env python
"""Скрипт для исправления транслитераций в файлах проекта.

Этот скрипт обнаруживает и заменяет кириллические символы
которые выглядят как латинские, на соответствующие латинские символы.
"""

import logging
import os
from pathlib import Path
from typing import Tuple

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

# Словарь замен кириллических символов
REPLACEMENTS = {
    # Транслитерационные замены кириллических символов на латинские
    "Moдyл'": "Модуль",
    "дekopatopamu": "декораторами",
    "pa6otbi": "работы",
    "HTTP-npokcu": "HTTP-прокси",
    "Coдepжut": "Содержит",
    "вcnomorateл'hbie": "вспомогательные",
    "ynpaвлehuя": "управления",
    "noвeдehuem": "поведением",
    "kлuehtoв": "клиентов",
    "npu": "при",
    "ucnoл'3oвahuu": "использовании",
    "npokcu-cepвepoв": "прокси-серверов",
    "Дekopatop": "Декоратор",
    "o6pa6otku": "обработки",
    "oшu6ok": "ошибок",
    "Пepexвatbiвaet": "Перехватывает",
    "pa3лuчhbie": "различные",
    "tunbi": "типы",
    "moryt": "могут",
    "вo3hukhyt'": "возникнуть",
    "kлuehtom": "клиентом",
    "лorupyet": "логирует",
    "Пpumeчahue": "Примечание",
    "Эtot": "Этот",
    "noдrotoвлeh": "подготовлен",
    "ucnoл'3oвahuя": "использования",
    "6yдyщux": "будущих",
    "вepcuяx": "версиях",
    "cuctembi": "системы",
    "pacшupehuu": "расширении",
    "фyhkцuohaл'hoctu": "функциональности",
    "Лorrep": "Логгер",
    "3anucu": "записи",
    "uhфopmaцuu": "информации",
    "Дekopupoвahhaя": "Декорированная",
    "фyhkцuя": "функция",
    "kotopaя": "которая",
    "nepexвatbiвaet": "перехватывает",
    "uckлючehuя": "исключения",
    "Ckpunt": "Скрипт",
    "3anycka": "запуска",
    "tectoв": "тестов",
    "yлyчшehhbim": "улучшенным",
    "nokpbituem": "покрытием",
    "koдa": "кода",
    "aвtomat_uчecku": "автоматически",
    "npumehяet": "применяет",
    "natчu": "патчи",
    "tectbi": "тесты",
    "u3mepehuem": "измерением",
    "nokpbituя": "покрытия",
    "rehepupyя": "генерируя",
    "HTML-otчet": "HTML-отчет",
    "Hactpoйka": "Настройка",
    "лorupoвahuя": "логирования",
    "Cnucok": "Список",
    "moдyлeй": "модулей",
    "tectupoвahuя": "тестирования",
    "ymoлчahuю": "умолчанию",
    "Гehepupoвat'": "Генерировать",
    "otчet": "отчет",
    "Muhumaл'hoe": "Минимальное",
    "tpe6yemoe": "требуемое",
    "Koд": "Код",
    "вo3вpata": "возврата",
    "ycnexe": "успехе",
    "Дo6aвляem": "Добавляем",
    "moдyлu": "модули",
    "onцuu": "опции",
    "onцuю": "опцию",
    "muhumaл'horo": "минимального",
    "дpyrue": "другие",
    "noлe3hbie": "полезные",
    "Oшu6ka": "Ошибка",
    "cжatuu": "сжатии",
    "ctpoku": "строки",
    "pacnakoвke": "распаковке",
    "Pacшupehhbiй": "Расширенный",
    "orpahuчehuя": "ограничения",
    "Пo3вoляet": "Позволяет",
    "ycтahaвлuвat'": "устанавливать",
    "koлuчectвy": "количеству",
    "3aдahhoe": "заданное",
    "3aдepжku": "задержки",
    "noддepжuвaet": "поддерживает",
    "aдantuвhbie": "адаптивные",
    "ctpatepuu": "стратегии",
    "otcpoчku": "отсрочки",
    "npeвbiшehuя": "превышения",
    "лumutoв": "лимитов",
    "Makcumaл'hoe": "Максимальное",
    "чucлo": "число",
    "вbi3oвoв": "вызовов",
    "Пepuoд": "Период",
    "вpemя": "время",
    "Иhuцuaлu3upyet": "Инициализирует",
    "лumutbi": "лимиты",
    "nepuoд": "период",
    "Bлokupyet": "Блокирует",
    "вbinoлhehue": "выполнение",
    "дocturhytbi": "достигнуты",
    "Metoд": "Метод",
    "otcлeжuвaet": "отслеживает",
    "uctopuю": "историю",
    "дo6aвляet": "добавляет",
    "ecлu": "если",
    "npoшлo": "прошло",
    "momehta": "момента",
    "Дocturhyt": "Достигнут",
    "teчehue": "течение",
    "Бbiлu": "Были",
    "nocлeдoвateл'hbie": "последовательные",
    "чepe3": "через",
    "Пpoвepяem": "Проверяем",
    "Ecлu": "Если",
    "npumehяem": "применяем",
    "эkcnohehцuaл'hyю": "экспоненциальную",
    "Ждem": "Ждем",
    "muhumaл'hbiй": "минимальный",
    "uhтepвaл": "интервал",
    "Oчuщaem": "Очищаем",
    "yctapeвшue": "устаревшие",
    "вbi3oвax": "вызовах",
    "koлuчectвo": "количество",
    "hyжho": "нужно",
    "дoждat'cя": "дождаться",
    "caмbiй": "самый",
    "вbiйдet": "выйдет",
    "npeдeлbi": "пределы",
    "Пpeвbiшeh": "Превышен",
    "лumut": "лимит",
}


def fix_transliterations(text: str) -> str:
    """Заменяет транслитерации в тексте.

    Args:
        text: Входной текст с возможными транслитерациями

    Returns:
        str: Текст с исправленными транслитерациями
    """
    result = text

    for transliteration, correct in REPLACEMENTS.items():
        result = result.replace(transliteration, correct)

    return result


def fix_file(file_path: Path) -> Tuple[int, str]:
    """Исправляет транслитерации в указанном файле.

    Args:
        file_path: Путь к файлу для исправления

    Returns:
        Tuple[int, str]: Количество замен и путь к файлу
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning(f"Ошибка декодирования файла: {file_path}")
        return 0, str(file_path)

    new_content = fix_transliterations(content)

    # Подсчитываем количество замен
    replacements = 0
    for trans in REPLACEMENTS:
        replacements += content.count(trans)

    if replacements > 0:
        file_path.write_text(new_content, encoding="utf-8")

    return replacements, str(file_path)


def process_files(directory: Path) -> int:
    """Обрабатывает файлы в директории с указанными расширениями.

    Args:
        directory: Путь к директории для обработки

    Returns:
        int: Количество исправленных файлов
    """
    extensions = [".py", ".md", ".txt", ".yaml", ".yml", ".json"]
    exclude = [
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
    ]

    fixed_files = 0

    for root, dirs, files in os.walk(directory):
        # Исключаем указанные директории
        dirs[:] = [d for d in dirs if d not in exclude]
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for file in files:
            file_suffix = Path(file).suffix
            if file_suffix in extensions:
                file_path = Path(root) / file
                replacements, _ = fix_file(file_path)
                if replacements > 0:
                    logger.info(f"Исправлено {replacements} в {file_path}")
                    fixed_files += 1

    return fixed_files


def main() -> None:
    """Основная функция скрипта."""
    # Получаем путь к корневой директории проекта
    project_root = Path(__file__).resolve().parent

    logger.info(f"Начинаем исправление в: {project_root}")

    # Обрабатываем все файлы в проекте
    fixed_files = process_files(project_root)

    logger.info(f"Завершено! Исправлено файлов: {fixed_files}")

    # Дополнительно обрабатываем некоторые специфические файлы
    problem_files = [
        project_root / "utils" / "data_compression.py",
        project_root / "utils" / "rate_limiter.py",
        project_root / "proxy_http" / "decorators.py",
        project_root / "run_tests_with_coverage.py",
    ]

    additional_fixed = 0
    for file_path in problem_files:
        if file_path.exists():
            replacements, _ = fix_file(file_path)
            if replacements > 0:
                logger.info(f"Исправлено {replacements} в {file_path}")
                additional_fixed += 1

    if additional_fixed > 0:
        logger.info(f"Дополнительно исправлено: {additional_fixed}")


if __name__ == "__main__":
    main()
