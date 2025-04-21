"""Mode selection handlers for the Telegram bot."""

import asyncio
import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from price_monitoring.telegram.bot.keyboards.mode_selection import (
    create_mode_selection_keyboard
)
from price_monitoring.telegram.bot.keyboards.main_menu import (
    create_main_menu_keyboard
)
from price_monitoring.telegram.bot.constants.trading_modes import (
    TRADING_MODES
)
from price_monitoring.telegram.bot.filters.callback_filters import (
    mode_callback_filter
)

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "select_mode")
async def process_select_mode(callback_query: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Выбрать режим".
    Показывает клавиатуру с доступными режимами работы.
    
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
    
    # Показываем клавиатуру с режимами
    keyboard = create_mode_selection_keyboard()
    await callback_query.message.edit_text(
        "\U0001F3AF Выберите режим работы:",
        reply_markup=keyboard
    )
    await callback_query.answer()


@router.callback_query(mode_callback_filter)
async def process_mode_selection(
    callback_query: types.CallbackQuery, state: FSMContext
):
    """
    Обработчик выбора конкретного режима работы.
    Сохраняет настройки режима в состоянии пользователя.
    
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
    
    # Проверка, что callback_data существует
    if not callback_query.data:
        await callback_query.answer("Error: Missing callback data.")
        return

    # Получаем режим из callback_data 
    # (mode_balance_boost, mode_medium_trader, mode_trade_pro)
    selected_mode = callback_query.data.split("_", 1)[1]
    
    # Проверяем наличие пользователя перед логированием
    user_id = (
        callback_query.from_user.id
        if callback_query.from_user
        else "Unknown"
    )
    
    # Проверяем существование выбранного режима
    if selected_mode in TRADING_MODES:
        mode_info = TRADING_MODES[selected_mode]
        
        # Сохраняем выбранный режим в state
        await state.update_data(
            selected_mode=selected_mode,
            min_profit=mode_info["min_profit"],
            max_profit=mode_info["max_profit"]
        )
        
        logger.info(
            f"User {user_id} selected trading mode: {mode_info['name']}"
        )
        
        # Отображаем информацию о выбранном режиме с улучшенным форматированием
        message_text = (
            f"{mode_info['emoji']} <b>Выбран режим: {mode_info['name']}</b>\n\n"
            f"<b>📋 Описание:</b>\n"
            f"{mode_info['description']}\n\n"
            f"<b>💰 Диапазон прибыли:</b> "
            f"${mode_info['min_profit']}-${mode_info['max_profit']}\n\n"
            f"✅ <i>Настройка сохранена. Теперь вы можете показать "
            f"предложения или настроить фильтры.</i>"
        )
        
        await callback_query.message.edit_text(
            message_text,
            parse_mode="HTML"
        )
        
        # Отвечаем на callback
        await callback_query.answer("Режим успешно выбран!")
        
        # Небольшая задержка перед возвратом в главное меню
        await asyncio.sleep(2)
        
        # Возвращаемся в главное меню путем редактирования текущего сообщения
        keyboard = create_main_menu_keyboard()
        await callback_query.message.edit_text(
            "Главное меню:",
            reply_markup=keyboard
        )
    else:
        logger.warning(
            f"User {user_id} selected unknown mode: {selected_mode}"
        )
        await callback_query.message.edit_text(
            "⚠️ Неизвестный режим. Пожалуйста, выберите из предложенных."
        )
        await callback_query.answer("Неизвестный режим")
        
        # Небольшая задержка перед возвратом в главное меню
        await asyncio.sleep(2)
        
        # Возвращаемся в главное меню путем редактирования текущего сообщения
        keyboard = create_main_menu_keyboard()
        await callback_query.message.edit_text(
            "Главное меню:",
            reply_markup=keyboard
        ) 