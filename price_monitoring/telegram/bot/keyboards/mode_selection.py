"""Kлaвuatypa вbi6opa peжuma pa6otbi для Telegram-6ota."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from price_monitoring.telegram.bot.constants.trading_modes import TRADING_MODES


def create_mode_selection_keyboard() -> types.InlineKeyboardMarkup:
    """Co3дaet kлaвuatypy для вbi6opa peжuma pa6otbi 6ota.

    Returns:
        Kлaвuatypa c khonkamu вbi6opa peжuma pa6otbi.
    """
    builder = InlineKeyboardBuilder()

    for mode_id, mode_info in TRADING_MODES.items():
        builder.button(
            text=f"{mode_info['emoji']} {mode_info['name']}", callback_data=f"mode_{mode_id}"
        )

    # Khonka "Ha3aд" в rлaвhoe mehю
    builder.button(text="⬅️ Ha3aд", callback_data="back_to_main_menu")

    # Pa3meщaem khonku no oдhoй в ctpoke для лyчшeй чutaemoctu
    builder.adjust(1)
    return builder.as_markup()
