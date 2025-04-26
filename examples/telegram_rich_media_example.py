"""Example script demonstrating how to use rich media and interactive features in the Telegram bot.

This script shows how to:
1. Send text messages with inline keyboards
2. Send images with captions
3. Send groups of images
4. Send videos and animations
5. Handle callback queries from inline buttons

Usage:
    python examples/telegram_rich_media_example.py
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from price_monitoring.market_types import MarketName
from price_monitoring.telegram.bot.abstract_command import AbstractCommand
from price_monitoring.telegram.bot.abstract_whitelist import AbstractWhitelist
from price_monitoring.telegram.models import InlineButton, ItemOfferNotification, NotificationType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# Simple whitelist implementation
class SimpleWhitelist(AbstractWhitelist):
    """Simple implementation of AbstractWhitelist for demonstration purposes."""

    def __init__(self, user_ids: list[int]):
        """Initialize with a list of user IDs."""
        self._user_ids = set(user_ids)

    async def get_members(self) -> set[int]:
        """Return the set of whitelisted user IDs."""
        return self._user_ids


# Example command implementation
class ExampleCommand(AbstractCommand):
    """Example command implementation."""

    def __init__(self, name: str, bot: Bot, notifications: list[ItemOfferNotification]):
        """Initialize with command name, bot instance, and notifications."""
        super().__init__(name)
        self._bot = bot
        self._notifications = notifications

    async def handler(self, message: types.Message) -> None:
        """Handle the command."""
        await message.reply(f"Command {self.name} received! Sending example notifications...")

        # Send each notification to the user
        for notification in self._notifications:
            await self._send_notification(message.chat.id, notification)

    async def _send_notification(self, chat_id: int, notification: ItemOfferNotification) -> None:
        """Send a notification to a user."""
        # Create inline keyboard if needed
        reply_markup = None
        if notification.buttons or notification.button_rows:
            reply_markup = self._create_inline_keyboard(notification)

        # Send based on notification type
        if notification.notification_type == NotificationType.TEXT:
            await self._bot.send_message(
                chat_id=chat_id,
                text=notification.text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        elif notification.notification_type == NotificationType.IMAGE:
            if notification.media_url:
                await self._bot.send_photo(
                    chat_id=chat_id,
                    photo=notification.media_url,
                    caption=notification.caption or notification.text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
        elif notification.notification_type == NotificationType.VIDEO:
            if notification.media_url:
                await self._bot.send_video(
                    chat_id=chat_id,
                    video=notification.media_url,
                    caption=notification.caption or notification.text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
        # Other types would be handled similarly

    def _create_inline_keyboard(self, notification: ItemOfferNotification) -> InlineKeyboardMarkup:
        """Create an inline keyboard from notification buttons."""
        keyboard = InlineKeyboardMarkup(row_width=2)

        # Add individual buttons
        if notification.buttons:
            for button in notification.buttons:
                if button.url:
                    keyboard.add(
                        InlineKeyboardButton(
                            text=button.text,
                            url=button.url,
                        )
                    )
                else:
                    keyboard.add(
                        InlineKeyboardButton(
                            text=button.text,
                            callback_data=button.callback_data,
                        )
                    )

        # Add button rows
        if notification.button_rows:
            for row in notification.button_rows:
                keyboard_row = []
                for button in row:
                    if button.url:
                        keyboard_row.append(
                            InlineKeyboardButton(
                                text=button.text,
                                url=button.url,
                            )
                        )
                    else:
                        keyboard_row.append(
                            InlineKeyboardButton(
                                text=button.text,
                                callback_data=button.callback_data,
                            )
                        )
                keyboard.row(*keyboard_row)

        return keyboard


# Callback query handler
async def handle_callback_query(query: types.CallbackQuery) -> None:
    """Handle callback queries from inline buttons."""
    # Extract the callback data
    callback_data = query.data

    # Log the callback
    logger.info(f"Received callback query: {callback_data} from user {query.from_user.id}")

    # Respond based on the callback data
    if callback_data.startswith("view_item:"):
        item_id = callback_data.split(":")[1]
        await query.answer(f"Viewing item {item_id}")
        await query.message.reply(f"Here are the details for item {item_id}...")

    elif callback_data.startswith("buy_item:"):
        item_id = callback_data.split(":")[1]
        await query.answer(f"Buying item {item_id}")
        await query.message.reply(f"Processing purchase for item {item_id}...")

    elif callback_data == "refresh":
        await query.answer("Refreshing data...")
        await query.message.reply("Data refreshed!")

    else:
        await query.answer(f"Unknown action: {callback_data}")


def create_example_notifications() -> list[ItemOfferNotification]:
    """Create example notifications with different types and features."""
    notifications = []

    # Text notification with buttons
    text_notification = ItemOfferNotification(
        market_name=MarketName.DMARKET,
        orig_price=100.0,
        sell_price=80.0,
        short_title="Example Text Notification",
        text="This is a text notification with buttons.",
        notification_type=NotificationType.TEXT,
        buttons=[
            InlineButton(text="View Item", callback_data="view_item:12345"),
            InlineButton(text="Buy Now", callback_data="buy_item:12345"),
            InlineButton(text="Visit DMarket", url="https://dmarket.com"),
        ],
    )
    notifications.append(text_notification)

    # Image notification
    image_notification = ItemOfferNotification(
        market_name=MarketName.DMARKET,
        orig_price=150.0,
        sell_price=120.0,
        short_title="Example Image Notification",
        text="This is an image notification.",
        notification_type=NotificationType.IMAGE,
        media_url="https://via.placeholder.com/500x300?text=Example+Item",
        caption="Example item with 20% discount!",
        button_rows=[
            [
                InlineButton(text="View", callback_data="view_item:67890"),
                InlineButton(text="Buy", callback_data="buy_item:67890"),
            ],
            [
                InlineButton(text="Refresh", callback_data="refresh"),
                InlineButton(text="DMarket", url="https://dmarket.com"),
            ],
        ],
    )
    notifications.append(image_notification)

    # Photo group notification
    photo_group_notification = ItemOfferNotification(
        market_name=MarketName.DMARKET,
        orig_price=200.0,
        sell_price=180.0,
        short_title="Example Photo Group",
        text="This is a photo group notification.",
        notification_type=NotificationType.PHOTO_GROUP,
        media_urls=[
            "https://via.placeholder.com/500x300?text=Image+1",
            "https://via.placeholder.com/500x300?text=Image+2",
            "https://via.placeholder.com/500x300?text=Image+3",
        ],
        caption="Multiple views of the item",
        buttons=[
            InlineButton(text="View All Images", callback_data="view_item:54321"),
        ],
    )
    notifications.append(photo_group_notification)

    # Video notification
    video_notification = ItemOfferNotification(
        market_name=MarketName.DMARKET,
        orig_price=300.0,
        sell_price=250.0,
        short_title="Example Video",
        text="This is a video notification.",
        notification_type=NotificationType.VIDEO,
        # Use a sample video URL - replace with an actual video URL for testing
        media_url="https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
        caption="Video demonstration of the item",
        buttons=[
            InlineButton(text="Buy Now", callback_data="buy_item:98765"),
        ],
    )
    notifications.append(video_notification)

    return notifications


async def main() -> None:
    """Main function to run the Telegram bot example."""
    # Load environment variables
    load_dotenv()

    # Get Telegram API token from environment
    telegram_token = os.getenv("TELEGRAM_API_TOKEN")
    if not telegram_token:
        logger.error("TELEGRAM_API_TOKEN environment variable is not set.")
        return

    # Get whitelist from environment
    whitelist_str = os.getenv("TELEGRAM_WHITELIST", "")
    try:
        whitelist = [int(uid.strip()) for uid in whitelist_str.split(",") if uid.strip()]
    except ValueError:
        logger.error(
            "Invalid TELEGRAM_WHITELIST format. Expected comma-separated list of integers."
        )
        return

    if not whitelist:
        logger.error("TELEGRAM_WHITELIST is empty. Add at least one user ID.")
        return

    logger.info(f"Starting Telegram bot example with whitelist: {whitelist}")

    try:
        # Create bot and dispatcher
        bot = Bot(token=telegram_token)
        dp = Dispatcher()

        # Create example notifications
        notifications = create_example_notifications()

        # Create commands
        [
            ExampleCommand("examples", bot, notifications),
        ]

        # Create whitelist
        SimpleWhitelist(whitelist)

        # Register callback query handler
        dp.callback_query.register(handle_callback_query)

        # Start the bot
        await bot.set_my_commands(
            [
                types.BotCommand(command="examples", description="Show example notifications"),
            ]
        )

        # Start polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        # Clean up resources
        logger.info("Shutting down...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
