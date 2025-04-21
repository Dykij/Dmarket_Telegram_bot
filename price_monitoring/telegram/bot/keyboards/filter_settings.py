"""Клавиатура настройки фильтров для Telegram-бота."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_filter_settings_keyboard() -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру для меню настройки фильтров.
    
    Returns:
        Клавиатура с кнопками настройки фильтров
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💵 Установить мин. прибыль", 
        callback_data="filter_set_min_profit"
    )
    builder.button(
        text="💸 Установить макс. прибыль", 
        callback_data="filter_set_max_profit"
    )
    builder.button(
        text="⬅️ Назад в главное меню",
        callback_data="back_to_main_menu"
    )
    builder.adjust(1)  # По одной кнопке в строке
    return builder.as_markup() 