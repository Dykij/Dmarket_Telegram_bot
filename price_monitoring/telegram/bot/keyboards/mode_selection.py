"""Клавиатура выбора режима работы для Telegram-бота."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from price_monitoring.telegram.bot.constants.trading_modes import TRADING_MODES


def create_mode_selection_keyboard() -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора режима работы бота.
    
    Returns:
        Клавиатура с кнопками выбора режима работы.
    """
    builder = InlineKeyboardBuilder()
    
    for mode_id, mode_info in TRADING_MODES.items():
        builder.button(
            text=f"{mode_info['emoji']} {mode_info['name']}",
            callback_data=f"mode_{mode_id}"
        )
    
    # Кнопка "Назад" в главное меню
    builder.button(
        text="⬅️ Назад",
        callback_data="back_to_main_menu"
    )
    
    # Размещаем кнопки по одной в строке для лучшей читаемости
    builder.adjust(1)
    return builder.as_markup() 