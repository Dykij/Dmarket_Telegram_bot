import asyncio
import logging
from typing import List, Optional

# Удалены неиспользуемые импорты telegram
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

# Removed direct import of env vars, should be passed during instantiation
# from common.env_var import TELEGRAM_API_TOKEN, TELEGRAM_WHITELIST

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Реализация бота Telegram на основе официальной библиотеки python-telegram-bot.

    Важно: Этот класс подготовлен для использования в будущих версиях системы
    и обеспечивает базовую функциональность для отправки уведомлений пользователям
    из белого списка. Сейчас в проекте используется реализация на основе aiogram.

    Attributes:
        bot: Экземпляр класса Bot из python-telegram-bot
        whitelist: Набор ID чатов пользователей, которым разрешено взаимодействие с ботом
    """

    def __init__(self, token: str, whitelist_ids: Optional[List[str]] = None):
        """
        Инициализирует бота Telegram.

        Args:
            token: Токен API Telegram бота.
            whitelist_ids: Список строковых ID чатов, которым разрешено взаимодействие с ботом.
        """
        if not token:
            raise ValueError("Telegram API token is required.")
        self.bot = Bot(token=token)
        # Convert whitelist IDs from string to int for comparison
        try:
            self.whitelist: set[int] = (
                set(int(uid.strip()) for uid in whitelist_ids if uid.strip())
                if whitelist_ids
                else set()
            )
        except ValueError as e:
            logger.error(f"Invalid Telegram whitelist ID found: {e}. Ensure all IDs are numeric.")
            self.whitelist = set()

        logger.info(
            f"Telegram Bot initialized. Whitelist: "
            f"{self.whitelist if self.whitelist else 'Disabled'}"
        )

    async def send_message(
        self, chat_id: int, text: str, parse_mode: Optional[str] = ParseMode.MARKDOWN
    ):
        """
        Отправляет сообщение конкретному пользователю с учетом белого списка.

        Args:
            chat_id: ID чата пользователя
            text: Текст сообщения
            parse_mode: Режим форматирования текста
        """
        if self.whitelist and chat_id not in self.whitelist:
            logger.warning(f"Attempted to send message to non-whitelisted chat_id: {chat_id}")
            return
        try:
            await self.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            logger.debug(f"Message sent to chat_id: {chat_id}")
        except TelegramAPIError as e:
            # Often related to Markdown parsing errors
            logger.error(
                f"Failed to send message to {chat_id} (BadRequest): {e}. Message: {text[:100]}..."
            )
            # Try sending as plain text as a fallback
            try:
                await self.bot.send_message(chat_id=chat_id, text=text, parse_mode=None)
                logger.info(f"Sent message to {chat_id} as plain text after Markdown failure.")
            except Exception as fallback_e:
                logger.error(
                    f"Failed to send message as plain text fallback to {chat_id}: {fallback_e}"
                )
        except Exception as e:
            logger.exception(f"Unexpected error sending message to {chat_id}: {e}")

    async def send_message_to_all(self, text: str, parse_mode: Optional[str] = ParseMode.MARKDOWN):
        """
        Отправляет сообщение всем пользователям из белого списка.

        Метод обеспечивает рассылку информации по всем пользователям,
        имеющим право на получение уведомлений. Используется для массовых
        оповещений о важных событиях или изменениях.

        Args:
            text: Текст сообщения
            parse_mode: Режим форматирования текста
        """
        if not self.whitelist:
            logger.warning("Cannot send message to all: Whitelist is empty or disabled.")
            return

        tasks = [self.send_message(chat_id, text, parse_mode) for chat_id in self.whitelist]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failure_count = len(results) - success_count

        logger.info(
            f"Message broadcast attempt to {len(self.whitelist)} users completed. "
            f"Success: {success_count}, Failures: {failure_count}"
        )

    # Optional: Add methods to handle commands or updates if needed later
    # async def start(self, update: telegram.Update, context: telegram.ext.CallbackContext):
    #     await update.message.reply_text('Hello! I am your DMarket arbitrage bot.')
