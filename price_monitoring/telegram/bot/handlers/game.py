"""Game selection handlers for the Telegram bot."""

import asyncio
import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from price_monitoring.telegram.bot.keyboards.game_selection import (
    create_game_selection_keyboard
)
from price_monitoring.telegram.bot.keyboards.main_menu import (
    create_main_menu_keyboard
)
from price_monitoring.telegram.bot.constants.games import (
    SUPPORTED_GAMES,
    GAME_EMOJIS
)
from price_monitoring.telegram.bot.filters.callback_filters import (
    game_callback_filter
)

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "select_games")
async def process_select_games(callback_query: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Выбрать игры".
    Показывает клавиатуру с доступными играми.
    
    Args:
        callback_query: Callback query от Telegram
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
    
    keyboard = create_game_selection_keyboard()
    await callback_query.message.edit_text(
        "🎮 <b>Выберите игру или игры</b>\n\n"
        "Выберите игру для поиска предложений или выберите все игры "
        "для поиска по всем поддерживаемым играм.\n\n"
        "<i>Поддерживаемые игры: CS2, Dota2, TF2, Rust</i>", 
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    # Отвечаем на callback, чтобы убрать 'часики' у кнопки
    await callback_query.answer()


@router.callback_query(game_callback_filter)
async def process_game_selection(
    callback_query: types.CallbackQuery, 
    state: FSMContext
):
    """
    Обработчик выбора конкретной игры или всех игр.
    Сохраняет выбор в состоянии пользователя.
    
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
    
    # Проверка, что callback_data существует (хотя lambda уже проверяет)
    if not callback_query.data:
        # Возвращаем правильное сообщение об ошибке
        await callback_query.answer("Error: Missing callback data.")
        return

    # Получаем игру из callback_data (cs2, dota2, all)
    selected_game = callback_query.data.split("_", 1)[1]

    # Проверяем наличие пользователя перед логированием
    user_id = (
        callback_query.from_user.id
        if callback_query.from_user
        else "Unknown"
    )
    
    # Получаем emoji для выбранной игры
    game_emoji = "✅" if selected_game == "all" else GAME_EMOJIS.get(
        selected_game.upper(), "🎮"
    )

    if selected_game == "all":
        log_message = f"User {user_id} selected all games."
        logger.info(log_message)
        # Сохраняем выбор в state
        await state.update_data(selected_games=SUPPORTED_GAMES)
        
        # Форматируем сообщение с выбором всех игр
        message_text = (
            f"{game_emoji} <b>Вы выбрали все игры</b>\n\n"
            f"Поиск будет осуществляться по всем поддерживаемым играм: "
            f"<b>{', '.join(SUPPORTED_GAMES)}</b>\n\n"
            f"<i>Для изменения выбора вернитесь в раздел выбора игр.</i>"
        )
        
        await callback_query.message.edit_text(
            message_text,
            parse_mode="HTML"
        )
        await callback_query.answer("Выбраны все игры")
    else:
        # Получаем правильное название игры (с учетом регистра)
        proper_game_name = next(
            (game for game in SUPPORTED_GAMES 
             if game.lower() == selected_game),
            selected_game.upper()
        )
        
        log_message = f"User {user_id} selected game: {selected_game}"
        logger.info(log_message)
        # Сохраняем выбор в state
        await state.update_data(selected_games=[proper_game_name])
        
        # Форматируем сообщение с выбором конкретной игры
        message_text = (
            f"{game_emoji} <b>Вы выбрали игру: {proper_game_name}</b>\n\n"
            f"Поиск будет осуществляться только по предметам этой игры.\n\n"
            f"<i>Для изменения выбора вернитесь в раздел выбора игр.</i>"
        )
        
        await callback_query.message.edit_text(
            message_text,
            parse_mode="HTML"
        )
        await callback_query.answer(f"Выбрана игра {proper_game_name}")

    # Небольшая задержка перед возвратом в главное меню
    await asyncio.sleep(2)
    
    # Возвращаемся в главное меню
    keyboard = create_main_menu_keyboard()
    await callback_query.message.edit_text(
        "Главное меню:",
        reply_markup=keyboard
    ) 