#!/usr/bin/env python
"""Скрипт для запуска тестов с улучшенным покрытием кода.

Этот скрипт автоматически применяет патчи для aioredis и запускает
тесты с измерением покрытия, генерируя HTML-отчет.
"""

import argparse
import logging
import subprocess
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_runner")


def run_tests_with_coverage(modules=None, html=True, min_coverage=80):
    """Запускает тесты с измерением покрытия кода.

    Args:
        modules: Список модулей для тестирования (по умолчанию все)
        html: Генерировать HTML-отчет о покрытии
        min_coverage: Минимальное требуемое покрытие кода

    Returns:
        int: Код возврата (0 при успехе)
    """
    cmd = ["pytest"]

    # Добавляем модули для покрытия
    if not modules:
        modules = ["price_monitoring", "common"]

    for module in modules:
        cmd.append(f"--cov={module}")

    # Добавляем опции для отчета о покрытии
    if html:
        cmd.append("--cov-report=html")

    # Добавляем опцию минимального покрытия
    cmd.append(f"--cov-fail-under={min_coverage}")

    # Добавляем другие полезные опции
    cmd.extend(["-v"])

    # Запускаем тесты
    try:
        logger.info(f"Запуск команды: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        logger.error(f"Ошибка при запуске тестов: {e}")
        return 1


def main():
    """Основная функция скрипта."""
    parser = argparse.ArgumentParser(description="Запуск тестов с измерением покрытия кода")
    parser.add_argument(
        "--modules",
        "-m",
        nargs="+",
        help="Список модулей для тестирования (по умолчанию: price_monitoring и common)",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Не генерировать HTML-отчет о покрытии",
    )
    parser.add_argument(
        "--min-coverage",
        type=int,
        default=80,
        help="Минимальное требуемое покрытие кода (по умолчанию: 80%%)",
    )
    args = parser.parse_args()

    # Запускаем тесты с покрытием
    exit_code = run_tests_with_coverage(
        modules=args.modules, html=not args.no_html, min_coverage=args.min_coverage
    )

    # Если тесты завершились успешно
    if exit_code == 0:
        logger.info("Тесты успешно пройдены!")
        logger.info("HTML-отчет о покрытии сгенерирован в директории coverage_html_report")
    else:
        logger.error(f"Ошибка при запуске тестов, код возврата: {exit_code}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
