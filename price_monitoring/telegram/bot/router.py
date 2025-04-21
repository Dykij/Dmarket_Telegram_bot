"""Router setup for the Telegram bot."""

import logging
from aiogram import Router

# Импортируем центральный роутер из menu
from price_monitoring.telegram.bot.menu import router as menu_router

logger = logging.getLogger(__name__)

# Основной роутер бота
router = Router()


def setup_router() -> Router:
    """
    Настраивает и возвращает основной роутер бота.
    
    Подключает центральный роутер меню, который содержит все обработчики.
    
    Returns:
        Настроенный роутер
    """
    # Подключаем центральный роутер меню, который уже содержит 
    # все остальные роутеры
    router.include_router(menu_router)
    
    logger.info("All handlers have been registered successfully")
    return router 