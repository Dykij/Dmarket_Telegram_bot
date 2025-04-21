"""Filter settings handlers for the Telegram bot."""

import asyncio
import logging
from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from price_monitoring.telegram.bot.keyboards.filter_settings import (
    create_filter_settings_keyboard
)
from price_monitoring.telegram.bot.states.filter_states import FilterStates

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "configure_filters")
async def process_configure_filters(callback_query: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Настроить фильтры".
    Показывает клавиатуру с настройками фильтров.
    
    Args:
        callback_query: Callback query от Telegram
    """
    # Проверка, что исходное сообщение существует
    if not callback_query.message or not isinstance(
        callback_query.message, types.Message
    ):
        await callback_query.answer(
            "Cannot process: "
            "original message not found or inaccessible."
        )
        return
    
    # Создаем клавиатуру с кнопками настройки фильтров
    keyboard = create_filter_settings_keyboard()
    
    await callback_query.message.edit_text(
        "🛠️ <b>Настройка фильтров</b>\n\n"
        "Выберите параметр для настройки:\n\n"
        "<i>Эти настройки будут использоваться для поиска "
        "выгодных предложений.</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()


def game_callback_filter(callback: types.CallbackQuery) -> bool:
    return callback.data is not None and callback.data.startswith("game_")

def mode_callback_filter(callback: types.CallbackQuery) -> bool:
    return callback.data is not None and callback.data.startswith("mode_")

def filter_callback_filter(callback: types.CallbackQuery) -> bool:
    return callback.data is not None and callback.data.startswith("filter_")

def pagination_callback_filter(callback: types.CallbackQuery) -> bool:
    return (callback.data is not None and 
            (callback.data.startswith("page_next_") or 
             callback.data.startswith("page_prev_")))


@router.callback_query(lambda c: c.data == "filter_set_min_profit")
async def process_set_min_profit(
    callback_query: types.CallbackQuery, state: FSMContext
):
    """
    Обработчик нажатия на кнопку установки минимальной прибыли.
    Запрашивает у пользователя ввод минимальной прибыли.
    
    Args:
        callback_query: Callback query от Telegram
        state: Объект управления состоянием
    """
    # Проверка, что исходное сообщение существует и доступно
    if not callback_query.message or not isinstance(
        callback_query.message, types.Message
    ):
        await callback_query.answer(
            "Cannot process: "
            "original message not found or inaccessible."
        )
        return
    
    await callback_query.message.edit_text(
        "💵 <b>Установка минимальной прибыли</b>\n\n"
        "Введите минимальное значение прибыли в долларах (например, 5):\n\n"
        "<i>Это значение будет использоваться для фильтрации предложений. "
        "Будут показаны только предметы с прибылью больше указанной.</i>",
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние ожидания ввода мин. прибыли
    await state.set_state(FilterStates.waiting_min_profit)
    await callback_query.answer()


@router.message(StateFilter(FilterStates.waiting_min_profit))
async def process_min_profit_value(
    message: types.Message, state: FSMContext
):
    """
    Обработчик ввода значения минимальной прибыли.
    Сохраняет указанное значение в состоянии пользователя.
    
    Args:
        message: Сообщение от пользователя
        state: Объект управления состоянием
    """
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, введите число. Например: 5 или 5.5"
        )
        return
    
    # Проверяем, что сообщение содержит число
    try:
        min_profit = float(message.text)
        if min_profit < 0:
            await message.reply(
                "❌ Значение прибыли не может быть отрицательным. "
                "Пожалуйста, введите положительное число."
            )
            return
        
        # Сохраняем значение в state
        await state.update_data(min_profit=min_profit)
        
        # Логируем изменение
        user_id = message.from_user.id if message.from_user else "Unknown"
        logger.info(f"User {user_id} set min_profit to {min_profit}")
        
        # Сбрасываем состояние
        await state.clear()
        
        # Отправляем сообщение об успехе
        confirm_message = await message.reply(
            f"✅ <b>Минимальная прибыль установлена: ${min_profit:.2f}</b>\n\n"
            f"Теперь при поиске предложений будут учитываться "
            f"только предметы с прибылью от ${min_profit:.2f}.",
            parse_mode="HTML"
        )
        
        # Небольшая задержка перед возвратом в меню фильтров
        await asyncio.sleep(2)
        
        # Возвращаемся в меню фильтров
        keyboard = create_filter_settings_keyboard()
        
        await confirm_message.reply(
            "🛠️ <b>Вернуться к настройке фильтров?</b>\n\n"
            "Вы можете продолжить настройку фильтров или вернуться "
            "в главное меню:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except ValueError:
        await message.reply(
            "❌ Пожалуйста, введите число. Например: 5 или 5.5"
        )


@router.callback_query(lambda c: c.data == "filter_set_max_profit")
async def process_set_max_profit(
    callback_query: types.CallbackQuery, state: FSMContext
):
    """
    Обработчик нажатия на кнопку установки максимальной прибыли.
    Запрашивает у пользователя ввод максимальной прибыли.
    
    Args:
        callback_query: Callback query от Telegram
        state: Объект управления состоянием
    """
    # Проверка, что исходное сообщение существует и доступно
    if not callback_query.message or not isinstance(
        callback_query.message, types.Message
    ):
        await callback_query.answer(
            "Cannot process: "
            "original message not found or inaccessible."
        )
        return
    
    await callback_query.message.edit_text(
        "💸 <b>Установка максимальной прибыли</b>\n\n"
        "Введите максимальное значение прибыли в долларах (например, 20):\n\n"
        "<i>Это значение будет использоваться для фильтрации предложений. "
        "Будут показаны только предметы с прибылью меньше указанной.</i>",
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние ожидания ввода макс. прибыли
    await state.set_state(FilterStates.waiting_max_profit)
    await callback_query.answer()


@router.message(StateFilter(FilterStates.waiting_max_profit))
async def process_max_profit_value(
    message: types.Message, state: FSMContext
):
    """
    Обработчик ввода значения максимальной прибыли.
    Сохраняет указанное значение в состоянии пользователя.
    
    Args:
        message: Сообщение от пользователя
        state: Объект управления состоянием
    """
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.reply(
            "❌ Пожалуйста, введите число. Например: 20 или 25.5"
        )
        return
    
    # Проверяем, что сообщение содержит число
    try:
        max_profit = float(message.text)
        if max_profit < 0:
            await message.reply(
                "❌ Значение прибыли не может быть отрицательным. "
                "Пожалуйста, введите положительное число."
            )
            return
        
        # Получаем текущие данные, чтобы проверить min_profit
        data = await state.get_data()
        min_profit = data.get("min_profit", 0)
        
        if max_profit < min_profit:
            await message.reply(
                f"❌ Максимальная прибыль должна быть больше минимальной "
                f"(${min_profit:.2f}). Пожалуйста, введите большее значение."
            )
            return
        
        # Сохраняем значение в state
        await state.update_data(max_profit=max_profit)
        
        # Логируем изменение
        user_id = message.from_user.id if message.from_user else "Unknown"
        logger.info(f"User {user_id} set max_profit to {max_profit}")
        
        # Сбрасываем состояние
        await state.clear()
        
        # Отправляем сообщение об успехе
        confirm_message = await message.reply(
            f"✅ <b>Максимальная прибыль установлена: ${max_profit:.2f}</b>\n\n"
            f"Теперь при поиске предложений будут учитываться "
            f"только предметы с прибылью от ${min_profit:.2f} "
            f"до ${max_profit:.2f}.",
            parse_mode="HTML"
        )
        
        # Небольшая задержка перед возвратом в меню фильтров
        await asyncio.sleep(2)
        
        # Возвращаемся в меню фильтров
        keyboard = create_filter_settings_keyboard()
        
        await confirm_message.reply(
            "🛠️ <b>Вернуться к настройке фильтров?</b>\n\n"
            "Вы можете продолжить настройку фильтров или вернуться "
            "в главное меню:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except ValueError:
        await message.reply(
            "❌ Пожалуйста, введите число. Например: 20 или 25.5"
        ) 