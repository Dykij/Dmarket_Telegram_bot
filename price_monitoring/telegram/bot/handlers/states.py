import logging
import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from ..keyboards import create_filter_settings_keyboard
from ..states import FilterStates

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(lambda c: c.data == "filter_set_min_profit")
async def process_set_min_profit(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    await callback_query.message.edit_text(
        "💵 <b>Установка минимальной прибыли</b>\n\n"
        "Введите минимальное значение прибыли в долларах (например, 5):\n\n"
        "<i>Это значение будет использоваться для фильтрации предложений. "
        "Будут показаны только предметы с прибылью больше указанной.</i>",
        parse_mode="HTML"
    )
    await state.set_state(FilterStates.waiting_min_profit)
    await callback_query.answer()

@router.message(StateFilter(FilterStates.waiting_min_profit))
async def process_min_profit_value(message: types.Message, state: FSMContext):
    if not message.text:
        await message.reply("❌ Пожалуйста, введите число. Например: 5 или 5.5")
        return
    try:
        min_profit = float(message.text)
        if min_profit < 0:
            await message.reply(
                "❌ Значение прибыли не может быть отрицательным. "
                "Пожалуйста, введите положительное число."
            )
            return
        await state.update_data(min_profit=min_profit)
        user_id = message.from_user.id if message.from_user else "Unknown"
        logger.info(f"User {user_id} set min_profit to {min_profit}")
        await state.clear()
        confirm_message = await message.reply(
            f"✅ <b>Минимальная прибыль установлена: ${min_profit:.2f}</b>\n\n"
            f"Теперь при поиске предложений будут учитываться "
            f"только предметы с прибылью от ${min_profit:.2f}.",
            parse_mode="HTML"
        )
        await asyncio.sleep(2)
        keyboard = create_filter_settings_keyboard()
        await confirm_message.reply(
            "🛠️ <b>Вернуться к настройке фильтров?</b>\n\n"
            "Вы можете продолжить настройку фильтров или вернуться в главное меню:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except ValueError:
        await message.reply("❌ Пожалуйста, введите число. Например: 5 или 5.5")

@router.callback_query(lambda c: c.data == "filter_set_max_profit")
async def process_set_max_profit(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    await callback_query.message.edit_text(
        "💸 <b>Установка максимальной прибыли</b>\n\n"
        "Введите максимальное значение прибыли в долларах (например, 20):\n\n"
        "<i>Это значение будет использоваться для фильтрации предложений. "
        "Будут показаны только предметы с прибылью меньше указанной.</i>",
        parse_mode="HTML"
    )
    await state.set_state(FilterStates.waiting_max_profit)
    await callback_query.answer()

@router.message(StateFilter(FilterStates.waiting_max_profit))
async def process_max_profit_value(message: types.Message, state: FSMContext):
    if not message.text:
        await message.reply("❌ Пожалуйста, введите число. Например: 20 или 25.5")
        return
    try:
        max_profit = float(message.text)
        if max_profit < 0:
            await message.reply(
                "❌ Значение прибыли не может быть отрицательным. "
                "Пожалуйста, введите положительное число."
            )
            return
        data = await state.get_data()
        min_profit = data.get("min_profit", 0)
        if max_profit < min_profit:
            await message.reply(
                f"❌ Максимальная прибыль должна быть больше минимальной "
                f"(${min_profit:.2f}). Пожалуйста, введите большее значение."
            )
            return
        await state.update_data(max_profit=max_profit)
        user_id = message.from_user.id if message.from_user else "Unknown"
        logger.info(f"User {user_id} set max_profit to {max_profit}")
        await state.clear()
        confirm_message = await message.reply(
            f"✅ <b>Максимальная прибыль установлена: ${max_profit:.2f}</b>\n\n"
            f"Теперь при поиске предложений будут учитываться "
            f"только предметы с прибылью от ${min_profit:.2f} до ${max_profit:.2f}.",
            parse_mode="HTML"
        )
        await asyncio.sleep(2)
        keyboard = create_filter_settings_keyboard()
        await confirm_message.reply(
            "🛠️ <b>Вернуться к настройке фильтров?</b>\n\n"
            "Вы можете продолжить настройку фильтров или вернуться в главное меню:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except ValueError:
        await message.reply("❌ Пожалуйста, введите число. Например: 20 или 25.5") 