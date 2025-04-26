"""Mode selection handlers for the Telegram bot."""

import asyncio
import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from i18n import _

from price_monitoring.telegram.bot.constants.trading_modes import TRADING_MODES
from price_monitoring.telegram.bot.filters.callback_filters import mode_callback_filter
from price_monitoring.telegram.bot.keyboards.main_menu import create_main_menu_keyboard
from price_monitoring.telegram.bot.keyboards.mode_selection import create_mode_selection_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "select_mode")
async def process_select_mode(callback_query: types.CallbackQuery):
    """Handler for the "Select mode" button.
    Shows a keyboard with available operating modes.

    Args:
        callback_query: Callback query from Telegram
    """
    # Check that the original message exists
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer(
            _("Cannot process: original message not found or inaccessible.")
        )
        return

    user_id = callback_query.from_user.id if callback_query.from_user else None
    user_data = callback_query.from_user.to_dict() if callback_query.from_user else None

    # Show keyboard with available modes
    keyboard = create_mode_selection_keyboard()
    await callback_query.message.edit_text(
        _("\U0001f3af Select operating mode:", user_id=user_id, user_data=user_data),
        reply_markup=keyboard,
    )
    await callback_query.answer()


@router.callback_query(mode_callback_filter)
async def process_mode_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for selecting a specific operating mode.
    Saves mode settings in the user's state.

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

    # Check that callback_data exists
    if not callback_query.data:
        await callback_query.answer(_("Error: Missing callback data."))
        return

    # Get mode from callback_data
    # (mode_balance_boost, mode_medium_trader, mode_trade_pro)
    selected_mode = callback_query.data.split("_", 1)[1]

    # Check for user presence before logging
    user_id = callback_query.from_user.id if callback_query.from_user else None
    user_data = callback_query.from_user.to_dict() if callback_query.from_user else None
    log_user_id = user_id if user_id is not None else "Unknown"

    # Check if the selected mode exists
    if selected_mode in TRADING_MODES:
        mode_info = TRADING_MODES[selected_mode]

        # Save the selected mode in state
        await state.update_data(
            selected_mode=selected_mode,
            min_profit=mode_info["min_profit"],
            max_profit=mode_info["max_profit"],
        )

        logger.info(f"User {log_user_id} selected trading mode: {mode_info['name']}")

        # Display information about the selected mode with improved formatting
        message_text = _(
            "{emoji} <b>Selected mode: {name}</b>\n\n"
            "<b>📋 Description:</b>\n"
            "{description}\n\n"
            "<b>💰 Profit range:</b> "
            "${min_profit}-${max_profit}\n\n"
            "✅ <i>Settings saved. Now you can show "
            "offers or configure filters.</i>",
            user_id=user_id,
            user_data=user_data,
        ).format(
            emoji=mode_info["emoji"],
            name=mode_info["name"],
            description=mode_info["description"],
            min_profit=mode_info["min_profit"],
            max_profit=mode_info["max_profit"],
        )

        await callback_query.message.edit_text(message_text, parse_mode="HTML")

        # Answer the callback
        await callback_query.answer(
            _("Mode successfully selected!", user_id=user_id, user_data=user_data)
        )

        # Small delay before returning to the main menu
        await asyncio.sleep(2)

        # Return to the main menu by editing the current message
        keyboard = create_main_menu_keyboard()
        await callback_query.message.edit_text(
            _("Main menu:", user_id=user_id, user_data=user_data), reply_markup=keyboard
        )
    else:
        logger.warning(f"User {log_user_id} selected unknown mode: {selected_mode}")
        await callback_query.message.edit_text(
            _(
                "⚠️ Unknown mode. Please select from the available options.",
                user_id=user_id,
                user_data=user_data,
            )
        )
        await callback_query.answer(_("Unknown mode", user_id=user_id, user_data=user_data))

        # Small delay before returning to the main menu
        await asyncio.sleep(2)

        # Return to the main menu by editing the current message
        keyboard = create_main_menu_keyboard()
        await callback_query.message.edit_text(
            _("Main menu:", user_id=user_id, user_data=user_data), reply_markup=keyboard
        )
