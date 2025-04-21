"""Main menu keyboard for the Telegram bot."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_main_menu_keyboard() -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню бота.
    
    Returns:
        Клавиатура с кнопками главного меню.
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📊 Выбрать режим", callback_data="select_mode"
    )
    builder.button(
        text="⚙️ Настроить фильтры", callback_data="configure_filters"
    )
    builder.button(
        text="🔍 Показать предложения", callback_data="show_offers"
    )
    builder.button(
        text="🎮 Выбрать игры", callback_data="select_games"
    )
    builder.button(
        text="❓ Помощь", callback_data="show_help"
    )
    # Расположим кнопки: 2 в ряд, 2 в ряд, последнюю отдельно
    builder.adjust(2, 2, 1)
    return builder.as_markup() 