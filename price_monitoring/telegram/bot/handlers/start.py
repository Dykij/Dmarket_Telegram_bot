"""Start and help command handlers for the Telegram bot."""

import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from i18n import _

from price_monitoring.telegram.bot.keyboards.main_menu import create_main_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def handle_start(message: types.Message):
    """Handler for the /start command.
    Sends a welcome message and the main menu.
    """
    # Check that message and user exist
    if not message.from_user:
        logger.warning("Received /start command without user info.")
        return

    user_id = message.from_user.id
    user_data = message.from_user.to_dict() if message.from_user else None
    logger.info(f"User {user_id} started the bot.")
    keyboard = create_main_menu_keyboard()

    # Create welcome message with formatting
    welcome_message = _(
        "👋 <b>Hello! I'm a DMarket monitoring bot.</b>\n\n"
        "I'll help you find profitable trading offers "
        "on the DMarket platform. You can:\n\n"
        "• <b>Select mode</b> - configure search strategy\n"
        "• <b>Configure filters</b> - specify profit range\n"
        "• <b>Show offers</b> - find profitable items\n"
        "• <b>Select games</b> - choose games to search\n\n"
        "<i>Select an action using the buttons below:</i>",
        user_id=user_id,
        user_data=user_data,
    )

    await message.answer(welcome_message, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("help"))
async def handle_help(message: types.Message):
    """Handler for the /help command.
    Sends detailed information about the bot's capabilities
    and instructions for use.
    """
    user_id = message.from_user.id if message.from_user else None
    user_data = message.from_user.to_dict() if message.from_user else None

    # Create message with detailed information about the bot
    help_text = _(
        "📚 <b>Help on using the bot</b>\n\n"
        "<b>Main features:</b>\n\n"
        "🔍 <b>Finding profitable offers</b> - the bot finds items "
        "on DMarket with the best buy/sell price ratio.\n\n"
        "<b>🎮 Supported games:</b>\n"
        "• 🔫 CS2 (Counter-Strike 2)\n"
        "• 🧙‍♂️ Dota 2\n"
        "• 🎩 Team Fortress 2 (TF2)\n"
        "• 🏝️ Rust\n\n"
        "<b>Operating modes:</b>\n"
        "• 💸 <b>Balance Boost</b> - items with small profit "
        "($1-5) and low risk\n"
        "• 💰 <b>Medium Trader</b> - items with medium profit ($5-20)\n"
        "• 📈 <b>Trade Pro</b> - rare items with high profit ($20+)\n\n"
        "<b>Commands:</b>\n"
        "• /start - Start the bot and show the main menu\n"
        "• /help - Show this help\n"
        "• /games - Open the game selection menu\n\n"
        "<b>How to use:</b>\n"
        "1. Choose an operating mode that matches your strategy\n"
        "2. Configure search filters (minimum/maximum profit)\n"
        "3. Select a game or all games to search\n"
        "4. Click 'Show offers' to search for profitable items\n"
        "5. View results using navigation buttons\n\n"
        "<i>The bot periodically updates data to search "
        "for new offers.</i>",
        user_id=user_id,
        user_data=user_data,
    )

    # Create keyboard with button to return to main menu
    builder = InlineKeyboardBuilder()
    builder.button(
        text=_("⬅️ Return to main menu", user_id=user_id, user_data=user_data),
        callback_data="back_to_main_menu",
    )
    keyboard = builder.as_markup()  # type: ignore

    # Send help
    await message.answer(help_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("games"))
async def handle_games(message: types.Message):
    """Handler for the /games command.
    Sends a menu for selecting games to search for offers.
    """
    # Check that message and user exist
    if not message.from_user:
        logger.warning("Received /games command without user info.")
        return

    user_id = message.from_user.id
    user_data = message.from_user.to_dict() if message.from_user else None
    logger.info(f"User {user_id} used /games command.")

    # Create keyboard directly instead of calling a function
    builder = InlineKeyboardBuilder()

    # List of supported games
    supported_games = ["CS2", "Dota2", "TF2", "Rust"]

    # Game emoji mapping
    game_emojis = {"CS2": "🔫", "Dota2": "🧙‍♂️", "TF2": "🎩", "Rust": "🏝️"}

    for game in supported_games:
        # Get emoji for the game
        emoji = game_emojis.get(game, "🎮")
        # Use game_ prefix for callback_data
        builder.button(text=f"{emoji} {game}", callback_data=f"game_{game.lower()}")

    # Button for selecting all games
    builder.button(
        text=_("✅ All games", user_id=user_id, user_data=user_data), callback_data="game_all"
    )

    # Back to main menu button
    builder.button(
        text=_("⬅️ Back", user_id=user_id, user_data=user_data), callback_data="back_to_main_menu"
    )

    builder.adjust(2)  # 2 buttons per row
    keyboard = builder.as_markup()  # type: ignore

    await message.answer(
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
