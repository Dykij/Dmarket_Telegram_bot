"""
Центральный модуль приложения Dmarket Telegram Bot.

Данный модуль объединяет все ключевые компоненты системы и
предоставляет единую точку входа для их инициализации и управления.
"""

import logging
from typing import Any, Dict, Optional

# Инициализация логгера
logger = logging.getLogger(__name__)

# Глобальные переменные состояния приложения
_initialized = False
_components = {}


class DmarketBot:
    """
    Основной класс приложения, который управляет всеми компонентами
    и предоставляет доступ к ним.
    """
    
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """
        Инициализирует экземпляр бота со всеми компонентами.
        
        Args:
            settings: Настройки приложения (опционально)
        """
        self.settings = settings
        self.components = {}
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Инициализирует все компоненты системы.
        
        Порядок инициализации:
        1. Конфигурация
        2. Соединения с БД (Redis, etc.)
        3. Хранилища данных
        4. Интернационализация
        5. Парсеры и обработчики
        6. Телеграм-бот
        
        Returns:
            True если инициализация успешна, иначе False
        """
        try:
            if self._initialized:
                logger.warning("Система уже инициализирована")
                return True
            
            # 1. Инициализация конфигурации
            from config import get_settings
            
            if self.settings:
                # Устанавливаем переданные настройки
                from config import update_settings
                update_settings(**self.settings)
            
            # Получаем настройки
            settings = get_settings()
            self.components["settings"] = settings
            
            # 2. Инициализация соединений с БД
            redis_client = await self._init_redis(settings)
            self.components["redis"] = redis_client
            
            # 3. Инициализация хранилищ данных
            from price_monitoring.storage.user_settings import UserSettingsStorage
            
            user_settings_storage = UserSettingsStorage(
                redis_client=redis_client,
                key_prefix="user_settings:",
                ttl=settings.redis_ttl if hasattr(settings, "redis_ttl") else 604800
            )
            self.components["user_settings_storage"] = user_settings_storage
            
            # 4. Инициализация системы интернационализации
            from i18n import setup_i18n
            
            setup_i18n(
                locale_dir=settings.i18n_locale_dir,
                default_language=settings.i18n_default_language,
                available_languages=settings.i18n_available_languages,
                user_settings_storage=user_settings_storage
            )
            
            # 5. Инициализация парсеров и обработчиков
            # TODO: Инициализация парсеров и обработчиков
            
            # 6. Инициализация Telegram-бота
            # TODO: Инициализация бота
            
            self._initialized = True
            logger.info("Система успешно инициализирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации системы: {e}", exc_info=True)
            return False
    
    async def _init_redis(self, settings):
        """
        Инициализирует соединение с Redis.
        
        Args:
            settings: Настройки приложения
            
        Returns:
            Клиент Redis
        """
        import redis.asyncio as redis
        
        try:
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=False  # Не декодируем ответы автоматически
            )
            
            # Проверка соединения
            await redis_client.ping()
            logger.info(f"Установлено соединение с Redis: {settings.redis_host}:{settings.redis_port}")
            
            return redis_client
        except Exception as e:
            logger.error(f"Ошибка при подключении к Redis: {e}", exc_info=True)
            raise
    
    async def start(self) -> bool:
        """
        Запускает все компоненты системы.
        
        Returns:
            True если запуск успешен, иначе False
        """
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return False
        
        try:
            # TODO: Запуск компонентов
            logger.info("Система запущена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при запуске системы: {e}", exc_info=True)
            return False
    
    async def stop(self) -> bool:
        """
        Останавливает все компоненты системы.
        
        Returns:
            True если остановка успешна, иначе False
        """
        if not self._initialized:
            logger.warning("Невозможно остановить неинициализированную систему")
            return False
        
        try:
            # Закрываем соединение с Redis
            if "redis" in self.components:
                await self.components["redis"].close()
            
            # TODO: Остановка других компонентов
            
            self._initialized = False
            logger.info("Система остановлена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при остановке системы: {e}", exc_info=True)
            return False
    
    def get_component(self, name: str) -> Any:
        """
        Возвращает компонент по имени.
        
        Args:
            name: Имя компонента
            
        Returns:
            Компонент или None, если компонент не найден
        """
        return self.components.get(name)


# Глобальный экземпляр бота для упрощения доступа
_bot_instance: Optional[DmarketBot] = None


def get_bot() -> DmarketBot:
    """
    Возвращает глобальный экземпляр бота.
    Если экземпляр не существует, создает новый.
    
    Returns:
        Экземпляр DmarketBot
    """
    global _bot_instance
    
    if _bot_instance is None:
        _bot_instance = DmarketBot()
    
    return _bot_instance


async def initialize_app(settings: Optional[Dict[str, Any]] = None) -> bool:
    """
    Инициализирует приложение.
    
    Args:
        settings: Настройки приложения (опционально)
        
    Returns:
        True если инициализация успешна, иначе False
    """
    bot = get_bot()
    if settings:
        bot.settings = settings
    
    return await bot.initialize()


async def start_app() -> bool:
    """
    Запускает приложение.
    
    Returns:
        True если запуск успешен, иначе False
    """
    bot = get_bot()
    return await bot.start()


async def stop_app() -> bool:
    """
    Останавливает приложение.
    
    Returns:
        True если остановка успешна, иначе False
    """
    bot = get_bot()
    return await bot.stop()
