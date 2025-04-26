"""
Internationalization (i18n) module for Dmarket Telegram Bot.
"""
Модуль интернационализации (i18n) для Dmarket Telegram Bot.

Предоставляет функциональность для перевода сообщений на разные языки,
определения языка пользователя и управления языковыми настройками.
"""

import logging
from typing import Any, Dict, Optional

from .translator import Translator
from .language_detector import LanguageDetector

__all__ = [
    'translator',
    'language_detector',
    'get_user_language',
    'set_user_language',
    'translate',
    '_',  # Алиас для функции translate для совместимости с gettext
]

logger = logging.getLogger(__name__)

# Инициализация компонентов i18n
translator = None
language_detector = None
_user_settings_storage = None


def setup_i18n(
    locale_dir: str = "locale",
    default_language: str = "en",
    available_languages: list = None,
    user_settings_storage = None
) -> None:
    """
    Инициализирует систему интернационализации.
    
    Args:
        locale_dir: Директория с файлами локализации
        default_language: Язык по умолчанию
        available_languages: Список доступных языков
        user_settings_storage: Экземпляр хранилища пользовательских настроек
    """
    global translator, language_detector, _user_settings_storage
    
    # Инициализируем переводчик
    translator = Translator(
        domain="messages",
        locale_dir=locale_dir,
        default_language=default_language
    )
    
    # Если список языков не указан, используем доступные языки из переводчика
    if available_languages is None:
        available_languages = translator.get_available_languages()
    
    # Инициализируем детектор языка
    language_detector = LanguageDetector(
        default_language=default_language,
        available_languages=available_languages
    )
    
    # Сохраняем хранилище пользовательских настроек
    _user_settings_storage = user_settings_storage
    
    logger.info(
        f"Система интернационализации инициализирована. "
        f"Язык по умолчанию: {default_language}. "
        f"Доступные языки: {available_languages}"
    )


async def get_user_language(user_id: int, user_data: Dict[str, Any] = None) -> str:
    """
    Получает предпочтительный язык пользователя.
    
    Проверяет язык в следующем порядке:
    1. Кэш детектора языка
    2. Сохраненные настройки пользователя (если доступны)
    3. Данные Telegram пользователя
    4. Язык по умолчанию
    
    Args:
        user_id: Telegram ID пользователя
        user_data: Данные пользователя из Telegram
        
    Returns:
        Код языка (например, 'en', 'ru')
    """
    global _user_settings_storage
    
    # Проверяем кэш детектора языка
    if user_id in language_detector.user_languages:
        return language_detector.user_languages[user_id]
    
    # Проверяем сохраненные настройки пользователя
    if _user_settings_storage is not None:
        try:
            user_settings = await _user_settings_storage.get_settings(user_id)
            if user_settings and "language" in user_settings:
                language = user_settings["language"]
                # Также кэшируем язык в детекторе
                language_detector.set_user_language(user_id, language)
                return language
        except Exception as e:
            logger.error(f"Ошибка при получении языка из хранилища настроек: {e}")
    
    # Определяем язык из данных Telegram
    if user_data:
        language = language_detector.detect_from_telegram(user_data)
        # Сохраняем язык в кэше
        language_detector.set_user_language(user_id, language)
        return language
    
    # Возвращаем язык по умолчанию
    return language_detector.default_language


async def set_user_language(user_id: int, language: str) -> bool:
    """
    Устанавливает предпочтительный язык пользователя.
    
    Args:
        user_id: Telegram ID пользователя
        language: Код языка (например, 'en', 'ru')
        
    Returns:
        True если язык успешно установлен, иначе False
    """
    global _user_settings_storage
    
    # Проверяем, что язык поддерживается
    if language not in language_detector.available_languages:
        logger.warning(f"Попытка установить неподдерживаемый язык: {language}")
        return False
    
    # Сохраняем язык в кэше детектора
    language_detector.set_user_language(user_id, language)
    
    # Сохраняем язык в хранилище настроек пользователя
    if _user_settings_storage is not None:
        try:
            success = await _user_settings_storage.update_setting(user_id, "language", language)
            if not success:
                logger.warning(f"Не удалось сохранить язык пользователя {user_id} в хранилище")
                return False
        except Exception as e:
            logger.error(f"Ошибка при сохранении языка пользователя {user_id}: {e}")
            return False
    
    logger.debug(f"Язык пользователя {user_id} установлен: {language}")
    return True


async def translate(message: str, user_id: Optional[int] = None, 
                  user_data: Dict[str, Any] = None, language: str = None) -> str:
    """
    Переводит сообщение для конкретного пользователя или на указанный язык.
    
    Args:
        message: Сообщение для перевода
        user_id: Telegram ID пользователя (опционально)
        user_data: Данные пользователя из Telegram (опционально)
        language: Код языка для перевода (имеет приоритет над user_id)
        
    Returns:
        Переведенное сообщение
    """
    if translator is None:
        logger.warning("Система интернационализации не инициализирована")
        return message
    
    # Если указан язык, используем его
    if language:
        return translator.translate(message, language)
    
    # Если указан user_id, получаем его язык
    if user_id is not None:
        user_language = await get_user_language(user_id, user_data)
        return translator.translate(message, user_language)
    
    # Если ничего не указано, используем язык по умолчанию
    return translator.translate(message)


# Алиас для функции translate для совместимости с gettext
_ = translate
This module provides functionality for translating messages to different languages
and detecting user language preferences.

Usage:
    from i18n import _
    
    # Simple translation
    message = _("Welcome to DMarket Telegram Bot!")
    
    # Translation with user context
    message = _("Welcome back!", user_id=123456789)
    
    # Translation with formatting
    message = _("Item {item_name} price changed to ${price}").format(
        item_name="AWP | Dragon Lore",
        price=1299.99
    )
"""

import os
from typing import Optional, Dict, Any

from .translator import Translator
from .language_detector import LanguageDetector

# Initialize the translator with default settings
_translator = Translator(
    domain="messages",
    locale_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale"),
    default_language="en"
)

# Initialize the language detector with default settings
_language_detector = LanguageDetector(
    default_language="en",
    available_languages=_translator.get_available_languages()
)

def _(message: str, user_id: Optional[int] = None, user_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Translate a message for a specific user.
    
    Args:
        message: Message to translate
        user_id: Telegram user ID
        user_data: Telegram user data
        
    Returns:
        Translated message
    """
    if user_id is not None:
        language = _language_detector.get_user_language(user_id, user_data)
    else:
        language = "en"
    
    return _translator.translate(message, language)

# Export the language detector for direct access
language_detector = _language_detector

# Export the translator for direct access
translator = _translator