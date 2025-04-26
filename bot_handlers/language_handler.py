"""Language handler module for the Dmarket Telegram Bot.

This module provides handlers for language selection and management
in the Telegram bot.
"""

import logging
from collections.abc import Awaitable
from typing import Any, Callable

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from i18n import _, language_detector

logger = logging.getLogger(__name__)

# Type alias for handler function
HandlerType = Callable[[types.Message, dict[str, Any]], Awaitable[None]]


async def language_command(message: types.Message, state: FSMContext = None) -> None:
    """Handle the /language command to change the user's language.

    Args:
        message: Telegram message object
        state: FSM context (not used in this handler)
    """
    user = message.from_user
    user_id = user.id

    # Create language selection keyboard
    keyboard = create_language_keyboard()

    # Send language selection message
    await message.reply(
        _("Please select your preferred language:", user_id=user_id, user_data=user.to_dict()),
        reply_markup=keyboard,
    )


def create_language_keyboard() -> InlineKeyboardMarkup:
    """Create an inline keyboard for language selection.

    Returns:
        InlineKeyboardMarkup with language options
    """
    keyboard = InlineKeyboardMarkup(row_width=1)

    # Add buttons for each available language
    for lang_code in language_detector.available_languages:
        lang_name = language_detector.get_language_name(lang_code)

        # Add flag emoji based on language code
        flag_emoji = get_flag_emoji(lang_code)
        button_text = f"{lang_name} {flag_emoji}"

        keyboard.add(InlineKeyboardButton(text=button_text, callback_data=f"lang_{lang_code}"))

    return keyboard


def get_flag_emoji(lang_code: str) -> str:
    """Get flag emoji for a language code.

    Args:
        lang_code: Language code (e.g., 'en', 'ru')

    Returns:
        Flag emoji for the language
    """
    flags = {
        "en": "🇬🇧",
        "ru": "🇷🇺",
        "uk": "🇺🇦",
        "de": "🇩🇪",
        "fr": "🇫🇷",
        "es": "🇪🇸",
        "it": "🇮🇹",
        "pt": "🇵🇹",
        "pl": "🇵🇱",
        "tr": "🇹🇷",
        "ar": "🇸🇦",
        "zh": "🇨🇳",
        "ja": "🇯🇵",
        "ko": "🇰🇷",
    }

    return flags.get(lang_code, "🌐")


async def language_callback(query: types.CallbackQuery, state: FSMContext = None) -> None:
    """Handle language selection callback.

    Args:
        query: Callback query from inline keyboard
        state: FSM context (not used in this handler)
    """
    user = query.from_user
    user_id = user.id

    # Extract language code from callback data
    callback_data = query.data
    if not callback_data.startswith("lang_"):
        await query.answer("Invalid callback data")
        return

    lang_code = callback_data.split("_")[1]

    # Set user's language preference
    if language_detector.set_user_language(user_id, lang_code):
        # Get language name for confirmation message
        lang_name = language_detector.get_language_name(lang_code)

        # Answer the callback query
        await query.answer(_("Language updated", user_id=user_id))

        # Edit the message to confirm language selection
        await query.message.edit_text(
            _("Language set to {}", user_id=user_id).format(lang_name), reply_markup=None
        )

        logger.info(f"User {user_id} changed language to {lang_code}")
    else:
        # Language not supported
        await query.answer(_("Language not supported", user_id=user_id))
        logger.warning(f"User {user_id} attempted to set unsupported language: {lang_code}")


def register_handlers(dp) -> None:
    """Register language handlers with the dispatcher.

    Args:
        dp: Aiogram dispatcher
    """
    # Register command handler
    dp.register_message_handler(language_command, commands=["language", "lang"])

    # Register callback handler
    dp.register_callback_query_handler(
        language_callback, lambda c: c.data and c.data.startswith("lang_")
    )

    logger.info("Language handlers registered")
