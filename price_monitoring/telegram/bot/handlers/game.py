"""Game selection handlers for the Telegram bot."""

import asyncio
import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from i18n import _

from price_monitoring.telegram.bot.constants.games import GAME_EMOJIS, SUPPORTED_GAMES
from price_monitoring.telegram.bot.filters.callback_filters import game_callback_filter
from price_monitoring.telegram.bot.keyboards.game_selection import create_game_selection_keyboard
from price_monitoring.telegram.bot.keyboards.main_menu import create_main_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "select_games")
async def process_select_games(callback_query: types.CallbackQuery):
    """Handler for the "Select games" button.
    Shows a keyboard with available games.

    Args:
        callback_query: Callback query from Telegram
    """
    # Check that the original message exists and is accessible
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer(
            _("Cannot process: original message not found or inaccessible.")
        )
        return

    user_id = callback_query.from_user.id if callback_query.from_user else None
    user_data = callback_query.from_user.to_dict() if callback_query.from_user else None

    keyboard = create_game_selection_keyboard()
    await callback_query.message.edit_text(
        _(
            "🎮 <b>Select a game or games</b>\n\n"
            "Select a game to search for offers or select all games "
            "to search across all supported games.\n\n"
            "<i>Supported games: CS2, Dota2, TF2, Rust</i>",
            user_id=user_id,
            user_data=user_data,
        ),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    # Answer the callback to remove the 'clock' icon from the button
    await callback_query.answer()


@router.callback_query(game_callback_filter)
async def process_game_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for selecting a specific game or all games.
    Saves the selection in the user's state.

    Args:
        callback_query: Callback query from Telegram
        state: State management object
    """
    # Check that the original message exists and is accessible
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer(
            _("Cannot process: original message not found or inaccessible.")
        )
        return

    # Check that callback_data exists (although lambda already checks)
    if not callback_query.data:
        # Return the correct error message
        await callback_query.answer(_("Error: Missing callback data."))
        return

    # Get the game from callback_data (cs2, dota2, all)
    selected_game = callback_query.data.split("_", 1)[1]

    # Check for user presence before logging
    user_id = callback_query.from_user.id if callback_query.from_user else None
    user_data = callback_query.from_user.to_dict() if callback_query.from_user else None
    log_user_id = user_id if user_id is not None else "Unknown"

    # Get emoji for the selected game
    game_emoji = "✅" if selected_game == "all" else GAME_EMOJIS.get(selected_game.upper(), "🎮")

    if selected_game == "all":
        log_message = f"User {log_user_id} selected all games."
        logger.info(log_message)
        # Save the selection in state
        await state.update_data(selected_games=SUPPORTED_GAMES)

        # Format the message with the selection of all games
        message_text = _(
            "{emoji} <b>You have selected all games</b>\n\n"
            "Search will be performed across all supported games: "
            "<b>{games}</b>\n\n"
            "<i>To change your selection, return to the game selection section.</i>",
            user_id=user_id,
            user_data=user_data,
        ).format(emoji=game_emoji, games=", ".join(SUPPORTED_GAMES))

        await callback_query.message.edit_text(message_text, parse_mode="HTML")
        await callback_query.answer(_("All games selected", user_id=user_id, user_data=user_data))
    else:
        # Get the proper game name (with correct case)
        proper_game_name = next(
            (game for game in SUPPORTED_GAMES if game.lower() == selected_game),
            selected_game.upper(),
        )

        log_message = f"User {log_user_id} selected game: {selected_game}"
        logger.info(log_message)
        # Save the selection in state
        await state.update_data(selected_games=[proper_game_name])

        # Format the message with the selection of a specific game
        message_text = _(
            "{emoji} <b>You have selected game: {game_name}</b>\n\n"
            "Search will be performed only for items from this game.\n\n"
            "<i>To change your selection, return to the game selection section.</i>",
            user_id=user_id,
            user_data=user_data,
        ).format(emoji=game_emoji, game_name=proper_game_name)

        await callback_query.message.edit_text(message_text, parse_mode="HTML")
        await callback_query.answer(
            _("Game {game_name} selected", user_id=user_id, user_data=user_data).format(
                game_name=proper_game_name
            )
        )

    # Small delay before returning to the main menu
    await asyncio.sleep(2)

    # Return to the main menu
    keyboard = create_main_menu_keyboard()
    await callback_query.message.edit_text(
        _("Main menu:", user_id=user_id, user_data=user_data), reply_markup=keyboard
    )
