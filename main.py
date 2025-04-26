"""
Главная точка входа в приложение Dmarket Telegram Bot.

Этот модуль обеспечивает запуск и остановку приложения,
настройку логирования и обработку сигналов операционной системы.
"""

import asyncio
import logging
import logging.config
import os
import signal
import sys
from pathlib import Path

import yaml

# Настройка корневой директории проекта
BASE_DIR = Path(__file__).resolve().parent

# Добавление корневой директории в sys.path для импортов
sys.path.insert(0, str(BASE_DIR))

# Импорт основных компонентов
from core import initialize_app, start_app, stop_app


def setup_logging(config_path: str = None) -> None:
    """
    Настраивает систему логирования.
    
    Args:
        config_path: Путь к файлу конфигурации логирования
    """
    config_path = config_path or os.path.join(BASE_DIR, "logging.yaml")
    
    if os.path.exists(config_path):
        with open(config_path, 'rt') as f:
            config = yaml.safe_load(f.read())
        
        logging.config.dictConfig(config)
    else:
        # Базовая конфигурация логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
    
    logging.info(f"Логирование настроено с использованием {config_path}")


def load_env(env_file: str = None) -> dict:
    """
    Загружает переменные окружения из файла.
    
    Args:
        env_file: Путь к файлу с переменными окружения
        
    Returns:
        Словарь с переменными окружения
    """
    env_vars = {}
    
    # Определяем файл окружения на основе режима работы
    if not env_file:
        environment = os.environ.get("ENVIRONMENT", "development")
        env_file = os.path.join(BASE_DIR, f"{environment}.env")
    
    # Если файл существует, загружаем переменные
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
    
    return env_vars


def setup_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """
    Настраивает обработчики сигналов ОС для корректного завершения работы.
    
    Args:
        loop: Цикл событий asyncio
    """
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(loop, s)))
    
    logging.info("Настроены обработчики сигналов")


async def shutdown(loop: asyncio.AbstractEventLoop, signal: int = None) -> None:
    """
    Корректно завершает работу приложения.
    
    Args:
        loop: Цикл событий asyncio
        signal: Сигнал, вызвавший завершение работы
    """
    if signal:
        logging.info(f"Получен сигнал {signal.name}, завершение работы...")
    
    # Останавливаем приложение
    await stop_app()
    
    # Отменяем все задачи
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Останавливаем цикл событий
    loop.stop()
    logging.info("Завершение работы выполнено")


async def main() -> None:
    """
    Основная функция запуска приложения.
    """
    # Настройка логирования
    setup_logging()
    
    try:
        # Загрузка переменных окружения
        env_vars = load_env()
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Инициализация приложения
        await initialize_app()
        
        # Запуск приложения
        await start_app()
        
        # Основной цикл приложения
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logging.info("Получен сигнал прерывания, завершение работы...")
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {e}", exc_info=True)
    finally:
        # Остановка приложения при выходе
        await stop_app()


if __name__ == "__main__":
    # Получение цикла событий
    loop = asyncio.get_event_loop()
    
    try:
        # Настройка обработчиков сигналов
        setup_signal_handlers(loop)
        
        # Запуск основной функции
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        # Закрытие цикла событий
        loop.close()
        logging.info("Приложение завершило работу")
