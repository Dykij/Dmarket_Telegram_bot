import subprocess

import pytest


def run_command(command: str) -> tuple[int, str, str]:
    """Запускает команду и возвращает результат (код возврата, stdout, stderr)"""
    process = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
    return process.returncode, process.stdout, process.stderr


def install_if_missing(package_name: str, install_command: str | None = None) -> bool:
    """Устанавливает пакет, если он отсутствует"""
    if not install_command:
        install_command = f"poetry add --group dev {package_name}"

    try:
        # Проверяем наличие пакета
        check_cmd = f'poetry run python -c "import {package_name.replace("-", "_")}"'
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            print(f"⚙️ Установка {package_name}...")
            install_result = subprocess.run(
                install_command, shell=True, capture_output=True, text=True, check=False
            )

            if install_result.returncode == 0:
                print(f"✅ {package_name} успешно установлен")
                return True
            else:
                print(f"❌ Ошибка при установке {package_name}:")
                print(install_result.stderr)
                return False
        return True
    except Exception as e:
        print(f"❌ Ошибка при проверке/установке {package_name}: {e}")
        return False


def install_required_tools():
    """Устанавливает все необходимые инструменты"""
    tools = [
        ("black", "black"),
        ("mypy", "mypy"),
        ("pylint", "pylint"),
        ("isort", "isort"),
        ("flake8", "flake8"),
        ("ruff", "ruff"),  # Добавляем Ruff
        ("bandit", "bandit"),
        ("detect_secrets", "detect-secrets"),
        ("vulture", "vulture"),
        ("autoflake", "autoflake"),
        ("pycodestyle", "pycodestyle"),
        ("pydocstyle", "pydocstyle"),
        ("radon", "radon"),
        ("interrogate", "interrogate"),
        ("pre_commit", "pre-commit"),
        ("pytest_cov", "pytest-cov"),
        ("safety", "safety"),
    ]

    installed = True
    for _, package_name in tools:
        if not install_if_missing(package_name):
            installed = False

    return installed


def pytest_sessionstart(session: pytest.Session) -> None:
    """Запускается перед началом тестовой сессии"""
    print("\n" + "=" * 80)
    print("Установка инструментов для проверки кода...")
    print("=" * 80)

    install_required_tools()

    print("\n" + "=" * 80)
    print("Запуск проверки кода перед выполнением тестов...")
    print("=" * 80)
    checks = [
        # Основные проверки
        ("Black (форматирование кода)", "poetry run black --check ."),
        ("MyPy (проверка типов)", "poetry run mypy ."),
        (
            "Pylint (проверка стиля кода)",
            "poetry run pylint price_monitoring common proxy_http tests",
        ),
        # Добавляем Ruff - комплексный быстрый линтер
        (
            "Ruff (комплексная проверка кода)",
            "poetry run ruff check .",
        ),
        (
            "Ruff Format (форматирование кода)",
            "poetry run ruff format --check .",
        ),
        ("Проверка импортов", "poetry run python -m pip check"),
        ("isort (проверка порядка импортов)", "poetry run isort --check-only --profile black ."),
        ("flake8 (проверка стиля и синтаксиса)", "poetry run flake8 ."),
        # Безопасность
        (
            "Bandit (проверка безопасности)",
            "poetry run bandit -r price_monitoring common proxy_http",
        ),
        ("Detect-secrets (поиск секретов в коде)", "poetry run detect-secrets scan"),
        # Качество кода
        ("Vulture (поиск мертвого кода)", "poetry run vulture price_monitoring common proxy_http"),
        (
            "Autoflake (удаление неиспользуемых импортов)",
            "poetry run autoflake --check --recursive price_monitoring common proxy_http tests",
        ),
        (
            "Pycodestyle (соответствие PEP 8)",
            "poetry run pycodestyle price_monitoring common proxy_http tests",
        ),
        (
            "Pydocstyle (проверка документации)",
            "poetry run pydocstyle price_monitoring common proxy_http",
        ),
        # Анализ сложности кода
        (
            "Radon (анализ цикломатической сложности)",
            "poetry run radon cc -a price_monitoring common proxy_http",
        ),
        # Документация
        (
            "Interrogate (проверка покрытия документацией)",
            "poetry run interrogate -v price_monitoring common proxy_http",
        ),
        # Проверки Git
        ("Pre-commit (проверка хуков)", "poetry run pre-commit run --all-files"),
    ]

    errors_found = False

    for check_name, command in checks:
        print(f"\n{'-' * 40}")
        print(f"Выполнение: {check_name}")
        print(f"{'-' * 40}")

        try:
            return_code, stdout, stderr = run_command(command)

            if return_code != 0:
                errors_found = True
                print(f"❌ {check_name} завершился c ошибками:")

                if stdout:
                    print("\nВывод:")
                    print(stdout)

                if stderr:
                    print("\nОшибки:")
                    print(stderr)
            else:
                print(f"✅ {check_name} успешно пройден")
        except Exception as e:
            print(f"⚠️ Ошибка при выполнении {check_name}: {e}")

            # Если команда не найдена, предложить установить соответствующий пакет
            if "flake8" in command and "not found" in str(e):
                print("Установка flake8...")
                run_command("poetry add --group dev flake8")
                print("Повторная проверка после установки flake8...")
                run_command(command)

            if "isort" in command and "not found" in str(e):
                print("Установка isort...")
                run_command("poetry add --group dev isort")
                print("Повторная проверка после установки isort...")
                run_command(command)

    print("\n" + "=" * 80)

    if errors_found:
        print("❌ Обнаружены проблемы в коде. Просмотрите вывод выше для подробностей.")
        print("=" * 80)
    else:
        print("✅ Все проверки успешно пройдены!")
        print("=" * 80)
