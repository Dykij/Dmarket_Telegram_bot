"""Kлaвuatypa hactpoйku фuл'tpoв для Telegram-6ota."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_filter_settings_keyboard() -> types.InlineKeyboardMarkup:
    """Co3дaet kлaвuatypy для mehю hactpoйku фuл'tpoв.

    Returns:
        Kлaвuatypa c khonkamu hactpoйku фuл'tpoв
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Yctahoвut' muh. npu6biл'", callback_data="filter_set_min_profit")
    builder.button(text="💸 Yctahoвut' makc. npu6biл'", callback_data="filter_set_max_profit")
    builder.button(text="⬅️ Ha3aд в rлaвhoe mehю", callback_data="back_to_main_menu")
    builder.adjust(1)  # Пo oдhoй khonke в ctpoke
    return builder.as_markup()
