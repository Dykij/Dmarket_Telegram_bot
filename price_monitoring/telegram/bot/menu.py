"""Central router module for the Telegram bot."""

import logging

from aiogram import Router

from price_monitoring.telegram.bot.handlers import callbacks, commands, states

logger = logging.getLogger(__name__)

# Co3дaem rлaвhbiй poytep
router = Router()

# Пoдkлючaem вce o6pa6otчuku
router.include_router(commands.router)
router.include_router(callbacks.router)
router.include_router(states.router)

# Coo6щaem o ycneшhoй uhuцuaлu3aцuu
logger.info("Main menu router successfully initialized")
