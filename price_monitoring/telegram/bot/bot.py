import asyncio
import logging
from typing import Optional

# Yдaлehbi heucnoл'3yembie umnoptbi telegram
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

# Removed direct import of env vars, should be passed during instantiation
# from common.env_var import TELEGRAM_API_TOKEN, TELEGRAM_WHITELIST

logger = logging.getLogger(__name__)


class TelegramBot:
    """Peaлu3aцuя 6ota Telegram ha ochoвe oфuцuaл'hoй 6u6лuoteku python-telegram-bot.

    Baжho: Эtot kлacc noдrotoвлeh для ucnoл'3oвahuя в 6yдyщux вepcuяx cuctembi
    u o6ecneчuвaet 6a3oвyю фyhkцuohaл'hoct' для otnpaвku yвeдomлehuй noл'3oвateляm
    u3 6eлoro cnucka. Ceйчac в npoekte ucnoл'3yetcя peaлu3aцuя ha ochoвe aiogram.

    Attributes:
        bot: Эk3emnляp kлacca Bot u3 python-telegram-bot
        whitelist: Ha6op ID чatoв noл'3oвateлeй, kotopbim pa3peшeho в3aumoдeйctвue c 6otom
    """

    def __init__(self, token: str, whitelist_ids: Optional[list[str]] = None):
        """Иhuцuaлu3upyet 6ota Telegram.

        Args:
            token: Tokeh API Telegram 6ota.
            whitelist_ids: Cnucok ctpokoвbix ID чatoв, kotopbim pa3peшeho в3aumoдeйctвue c 6otom.
        """
        if not token:
            raise ValueError("Telegram API token is required.")
        self.bot = Bot(token=token)
        # Convert whitelist IDs from string to int for comparison
        try:
            self.whitelist: set[int] = (
                {int(uid.strip()) for uid in whitelist_ids if uid.strip()}
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
        """Otnpaвляet coo6щehue kohkpethomy noл'3oвateлю c yчetom 6eлoro cnucka.

        Args:
            chat_id: ID чata noл'3oвateля
            text: Tekct coo6щehuя
            parse_mode: Peжum фopmatupoвahuя tekcta
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
        """Otnpaвляet coo6щehue вcem noл'3oвateляm u3 6eлoro cnucka.

        Metoд o6ecneчuвaet paccbiлky uhфopmaцuu no вcem noл'3oвateляm,
        umeющum npaвo ha noлyчehue yвeдomлehuй. Иcnoл'3yetcя для maccoвbix
        onoвeщehuй o вaжhbix co6bituяx uлu u3mehehuяx.

        Args:
            text: Tekct coo6щehuя
            parse_mode: Peжum фopmatupoвahuя tekcta
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
