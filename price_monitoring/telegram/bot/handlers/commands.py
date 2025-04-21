import logging
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..keyboards import create_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def handle_start(message: types.Message):

    if not message.from_user:

        logger.warning("Received /start command without user info.")

        return

    user_id = message.from_user.id

    logger.info(f"User {user_id} started the bot.")

    keyboard = create_main_menu_keyboard()

    welcome_message = (

        "👋 <b>Привет! Я бот для мониторинга DMarket.</b>\n\n"

        "Я помогу вам найти выгодные предложения для трейдинга "

        "на площадке DMarket. Вы можете:\n\n"

        "• <b>Выбрать режим</b> - настроить стратегию поиска\n"

        "• <b>Настроить фильтры</b> - указать диапазон прибыли\n"

        "• <b>Показать предложения</b> - найти выгодные предметы\n"

        "• <b>Выбрать игры</b> - выбрать игры для поиска\n\n"

        "<i>Выберите действие, используя кнопки ниже:</i>"

    )

    await message.answer(welcome_message, reply_markup=keyboard, parse_mode="HTML")



@router.message(Command("help"))
async def handle_help(message: types.Message):

    help_text = (

        "📚 <b>Помощь по использованию бота</b>\n\n"

        "<b>Основные возможности:</b>\n\n"

        "🔍 <b>Поиск выгодных предложений</b> - бот находит предметы на DMarket "

        "с наилучшим соотношением цены покупки и продажи.\n\n"

        "🎮 <b>Поддерживаемые игры:</b>\n"

        "• 🔫 CS2 (Counter-Strike 2)\n"

        "• 🧙‍♂️ Dota 2\n"

        "• 🎩 Team Fortress 2 (TF2)\n"

        "• 🏝️ Rust\n\n"

        "<b>Режимы работы:</b>\n"

        "• 💸 <b>Разгон баланса</b> - предметы с небольшой прибылью ($1-5) и низким риском\n"

        "• 💰 <b>Средний трейдер</b> - предметы со средней прибылью ($5-20)\n"

        "• 📈 <b>Trade Pro</b> - редкие предметы с высокой прибылью ($20+)\n\n"

        "<b>Команды:</b>\n"

        "• /start - Запустить бота и показать главное меню\n"

        "• /help - Показать эту справку\n\n"

        "<b>Как пользоваться:</b>\n"

        "1. Выберите режим работы, соответствующий вашей стратегии\n"

        "2. Настройте фильтры для поиска (минимальная/максимальная прибыль)\n"

        "3. Выберите игру или все игры для поиска\n"

        "4. Нажмите 'Показать предложения' для поиска выгодных предметов\n"

        "5. Просматривайте результаты с помощью кнопок навигации\n\n"

        "<i>Бот периодически обновляет данные для поиска новых предложений.</i>"

    )

    builder = InlineKeyboardBuilder()

    builder.button(text="⬅️ Вернуться в главное меню", callback_data="back_to_main_menu")

    keyboard = builder.as_markup()

    await message.answer(help_text, reply_markup=keyboard, parse_mode="HTML") 