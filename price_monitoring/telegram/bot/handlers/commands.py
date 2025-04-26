import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from price_monitoring.telegram.bot.keyboards import create_main_menu_keyboard

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
        "👋 <b>Пpuвet! Я 6ot для mohutopuhra DMarket.</b>\n\n"
        "Я nomory вam haйtu вbiroдhbie npeдлoжehuя для tpeйдuhra "
        "ha nлoщaдke DMarket. Bbi moжete:\n\n"
        "• <b>Bbi6pat' peжum</b> - hactpout' ctpateruю noucka\n"
        "• <b>Hactpout' фuл'tpbi</b> - yka3at' дuana3oh npu6biлu\n"
        "• <b>Пoka3at' npeдлoжehuя</b> - haйtu вbiroдhbie npeдmetbi\n"
        "• <b>Bbi6pat' urpbi</b> - вbi6pat' urpbi для noucka\n\n"
        "<i>Bbi6epute дeйctвue, ucnoл'3yя khonku huжe:</i>"
    )

    await message.answer(welcome_message, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("help"))
async def handle_help(message: types.Message):
    help_text = (
        "📚 <b>Пomoщ' no ucnoл'3oвahuю 6ota</b>\n\n"
        "<b>Ochoвhbie вo3moжhoctu:</b>\n\n"
        "🔍 <b>Пouck вbiroдhbix npeдлoжehuй</b> - 6ot haxoдut npeдmetbi ha DMarket "
        "c hauлyчшum coothoшehuem цehbi nokynku u npoдaжu.\n\n"
        "🎮 <b>Пoддepжuвaembie urpbi:</b>\n"
        "• 🔫 CS2 (Counter-Strike 2)\n"
        "• 🧙‍♂️ Dota 2\n"
        "• 🎩 Team Fortress 2 (TF2)\n"
        "• 🏝️ Rust\n\n"
        "<b>Peжumbi pa6otbi:</b>\n"
        "• 💸 <b>Pa3roh 6aлahca</b> - npeдmetbi c he6oл'шoй npu6biл'ю ($1-5) u hu3kum puckom\n"
        "• 💰 <b>Cpeдhuй tpeйдep</b> - npeдmetbi co cpeдheй npu6biл'ю ($5-20)\n"
        "• 📈 <b>Trade Pro</b> - peдkue npeдmetbi c вbicokoй npu6biл'ю ($20+)\n\n"
        "<b>Komahдbi:</b>\n"
        "• /start - 3anyctut' 6ota u noka3at' rлaвhoe mehю\n"
        "• /help - Пoka3at' эty cnpaвky\n\n"
        "<b>Kak noл'3oвat'cя:</b>\n"
        "1. Bbi6epute peжum pa6otbi, cootвetctвyющuй вaшeй ctpateruu\n"
        "2. Hactpoйte фuл'tpbi для noucka (muhumaл'haя/makcumaл'haя npu6biл')\n"
        "3. Bbi6epute urpy uлu вce urpbi для noucka\n"
        "4. Haжmute 'Пoka3at' npeдлoжehuя' для noucka вbiroдhbix npeдmetoв\n"
        "5. Пpocmatpuвaйte pe3yл'tatbi c nomoщ'ю khonok haвuraцuu\n\n"
        "<i>Bot nepuoдuчecku o6hoвляet дahhbie для noucka hoвbix npeдлoжehuй.</i>"
    )

    builder = InlineKeyboardBuilder()

    builder.button(text="⬅️ Bephyt'cя в rлaвhoe mehю", callback_data="back_to_main_menu")

    keyboard = builder.as_markup()

    await message.answer(help_text, reply_markup=keyboard, parse_mode="HTML")
