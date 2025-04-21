"""Game selection keyboard for the Telegram bot."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from price_monitoring.telegram.bot.constants.games import (
    SUPPORTED_GAMES, 
    GAME_EMOJIS
)


def create_game_selection_keyboard() -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора игр.
    
    Returns:
        Клавиатура с кнопками выбора игр.
    """
    builder = InlineKeyboardBuilder()
    
    for game in SUPPORTED_GAMES:
        # Get emoji for the game
        emoji = GAME_EMOJIS.get(game, "🎮")
        # Используем префикс game_ для callback_data
        builder.button(
            text=f"{emoji} {game}", 
            callback_data=f"game_{game.lower()}"
        )
    
    # Кнопка для выбора всех игр
    builder.button(text="✅ Все игры", callback_data="game_all")
    
    # Кнопка Назад в главное меню
    builder.button(text="⬅️ Назад", callback_data="back_to_main_menu")
    
    builder.adjust(2)  # По 2 кнопки в ряд
    return builder.as_markup() 