"""Central router module for the Telegram bot."""

import logging
from aiogram import Router
from price_monitoring.telegram.bot.handlers import commands, callbacks, states

logger = logging.getLogger(__name__)

# Создаем главный роутер
router = Router()

# Подключаем все обработчики
router.include_router(commands.router)
router.include_router(callbacks.router)
router.include_router(states.router)

# Сообщаем о успешной инициализации
logger.info("Main menu router successfully initialized") 