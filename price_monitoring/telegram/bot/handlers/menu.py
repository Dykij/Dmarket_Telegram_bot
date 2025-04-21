"""Central router module for the Telegram bot."""

import logging
from aiogram import Router

# Импортируем все обработчики из соответствующих модулей
from price_monitoring.telegram.bot.handlers import (
    start, mode, game, filters, offers, navigation
)

# Создаем логгер
logger = logging.getLogger(__name__)

# Создаем главный роутер
router = Router()

# Подключаем все дочерние роутеры
router.include_router(start.router)
router.include_router(mode.router)
router.include_router(game.router)
router.include_router(filters.router)
router.include_router(offers.router)
router.include_router(navigation.router)

# Сообщаем о успешной инициализации
logger.info("Main menu router successfully initialized") 