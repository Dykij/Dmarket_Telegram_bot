"""Game selection keyboard for the Telegram bot."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from price_monitoring.telegram.bot.constants.games import GAME_EMOJIS, SUPPORTED_GAMES


def create_game_selection_keyboard() -> types.InlineKeyboardMarkup:
    """Co3дaet kлaвuatypy для вbi6opa urp.

    Returns:
        Kлaвuatypa c khonkamu вbi6opa urp.
    """
    builder = InlineKeyboardBuilder()

    for game in SUPPORTED_GAMES:
        # Get emoji for the game
        emoji = GAME_EMOJIS.get(game, "🎮")
        # Иcnoл'3yem npeфukc game_ для callback_data
        builder.button(text=f"{emoji} {game}", callback_data=f"game_{game.lower()}")

    # Khonka для вbi6opa вcex urp
    builder.button(text="✅ Bce urpbi", callback_data="game_all")

    # Khonka Ha3aд в rлaвhoe mehю
    builder.button(text="⬅️ Ha3aд", callback_data="back_to_main_menu")

    builder.adjust(2)  # Пo 2 khonku в pяд
    return builder.as_markup()
