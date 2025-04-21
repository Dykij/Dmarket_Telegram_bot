"""Offer display and pagination handlers for the Telegram bot."""

import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from price_monitoring.telegram.bot.keyboards.pagination import (
    create_pagination_keyboard
)
from price_monitoring.telegram.bot.keyboards.main_menu import (
    create_main_menu_keyboard
)
from price_monitoring.telegram.bot.formatters.offer_formatter import (
    format_offers_message
)
from price_monitoring.telegram.bot.states.filter_states import FilterStates
from price_monitoring.telegram.bot.constants.settings import PAGE_SIZE
from price_monitoring.telegram.bot.constants.modes import TRADING_MODES

# Импортируем клиент DMarket API
from price_monitoring.parsers.dmarket_api import dmarket_api_client

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "show_offers")
async def process_show_offers(
    callback_query: types.CallbackQuery, 
    state: FSMContext
):
    """
    Обработчик нажатия на кнопку "Показать предложения".
    Выполняет поиск предложений на основе выбранных параметров.
    
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
    
    # Получаем данные о настройках пользователя из state
    user_data = await state.get_data()
    
    # Значения по умолчанию
    selected_mode = user_data.get("selected_mode", "balance_boost")
    selected_games = user_data.get("selected_games", ["CS2"])
    min_profit = float(user_data.get("min_profit", 1))
    max_profit = float(user_data.get("max_profit", 100))
    
    # Определяем название режима, если выбран
    mode_name = "не выбран"
    mode_emoji = "\U00002753"  # ❓
    if selected_mode in TRADING_MODES:
        mode_info = TRADING_MODES[selected_mode]
        mode_name = mode_info["name"]
        mode_emoji = mode_info["emoji"]
    
    # Форматируем список игр для отображения
    games_str = ", ".join(selected_games) if selected_games else "не выбраны"
    
    # Форматируем поиск игры
    search_game = "cs2"  # По умолчанию CS2
    if selected_games and len(selected_games) == 1:
        search_game = selected_games[0].lower()
    
    # Формируем сообщение с параметрами поиска
    message_text = (
        f"🔍 <b>Поиск выгодных предложений</b>\n\n"
        f"<b>Параметры поиска:</b>\n"
        f"{mode_emoji} <b>Режим:</b> {mode_name}\n"
        f"🎮 <b>Игры:</b> {games_str}\n"
        f"💰 <b>Прибыль:</b> от <b>${min_profit:.2f}</b> "
        f"до <b>${max_profit:.2f}</b>\n\n"
        f"<i>Идет поиск предложений... это может занять некоторое время.</i>\n"
        f"<i>Результаты поиска будут отправлены отдельным сообщением.</i>"
    )
    
    await callback_query.message.edit_text(
        message_text,
        parse_mode="HTML"
    )
    
    # Отвечаем на callback, чтобы убрать 'часики' у кнопки
    await callback_query.answer("Начат поиск предложений...")
    
    try:
        # Поиск арбитражных возможностей с помощью API Dmarket
        search_result = await dmarket_api_client.find_arbitrage_opportunities(
            game=search_game,
            min_profit=min_profit,
            max_profit=max_profit,
            limit=PAGE_SIZE
        )
        
        offers = search_result.get("items", [])
        cursor = search_result.get("cursor")
        has_next_page = search_result.get("has_next_page", False)
        
        # Сохраняем результаты поиска в state для пагинации
        await state.update_data(
            offers_page=1,
            offers_cursor=cursor,
            offers_game=search_game,
            offers_min_profit=min_profit,
            offers_max_profit=max_profit,
            offers_has_next_page=has_next_page
        )
        
        # Устанавливаем состояние просмотра предложений
        await state.set_state(FilterStates.browsing_offers)
        
        # Форматируем текст сообщения с результатами
        results_text = format_offers_message(
            offers, 
            1, 
            10 if has_next_page else 1
        )
        
        # Создаем клавиатуру с кнопками навигации
        keyboard = create_pagination_keyboard(
            page=1,
            total_pages=10 if has_next_page else 1,
            has_next_page=has_next_page,
            has_prev_page=False
        )
        
        # Отправляем результаты поиска с клавиатурой навигации
        await callback_query.message.answer(
            results_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error searching for offers: {e}")
        await callback_query.message.answer(
            "❌ <b>Ошибка при поиске предложений</b>\n\n"
            f"Произошла ошибка при поиске предложений:\n"
            f"<code>{str(e)}</code>\n\n"
            f"<i>Пожалуйста, попробуйте позже или обратитесь "
            f"к администратору.</i>",
            parse_mode="HTML",
            reply_markup=create_main_menu_keyboard()
        )


# Фильтр для callback_query, связанных с пагинацией
def pagination_callback_filter(callback: types.CallbackQuery) -> bool:
    """
    Фильтр для callback_query, связанных с пагинацией.
    
    Args:
        callback: Callback query от Telegram
        
    Returns:
        True если callback_data связан с пагинацией, иначе False
    """
    return (callback.data is not None and 
            (callback.data.startswith("page_next_") or 
             callback.data.startswith("page_prev_")))


@router.callback_query(pagination_callback_filter)
async def process_pagination(
    callback_query: types.CallbackQuery, 
    state: FSMContext
):
    """
    Обработчик нажатия на кнопки пагинации "Вперед" и "Назад".
    
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
    
    # Получаем текущие настройки из state
    user_data = await state.get_data()
    current_page = user_data.get("offers_page", 1)
    cursor = user_data.get("offers_cursor")
    game = user_data.get("offers_game", "cs2")
    min_profit = user_data.get("offers_min_profit", 1.0)
    max_profit = user_data.get("offers_max_profit", 100.0)
    
    # Определяем направление (вперед/назад)
    is_next = callback_query.data.startswith("page_next_")
    
    # Для кнопки "Назад" нам нужно перейти на предыдущую страницу
    if not is_next and current_page > 1:
        # Вычисляем новую страницу
        new_page = current_page - 1
        # Для предыдущей страницы нам нужно сгенерировать предыдущий курсор
        prev_cursor = f"page_{new_page - 1}" if new_page > 1 else None
        
        # Обновляем состояние
        await state.update_data(
            offers_page=new_page,
            offers_cursor=prev_cursor
        )
        
        # Имитация загрузки предыдущей страницы (запрос к API)
        search_result = await dmarket_api_client.find_arbitrage_opportunities(
            game=game,
            min_profit=min_profit,
            max_profit=max_profit,
            limit=PAGE_SIZE,
            cursor=prev_cursor
        )
        
        offers = search_result.get("items", [])
        next_cursor = search_result.get("cursor")
        has_next_page = True  # На предыдущей странице всегда есть следующая
        
        # Обновляем курсор в state
        await state.update_data(offers_cursor=next_cursor)
    
    # Для кнопки "Вперед" нам нужно использовать сохраненный курсор
    elif is_next and cursor:
        # Вычисляем новую страницу
        new_page = current_page + 1
        
        # Загружаем следующую страницу с использованием курсора
        search_result = await dmarket_api_client.find_arbitrage_opportunities(
            game=game,
            min_profit=min_profit,
            max_profit=max_profit,
            limit=PAGE_SIZE,
            cursor=cursor
        )
        
        offers = search_result.get("items", [])
        next_cursor = search_result.get("cursor")
        has_next_page = search_result.get("has_next_page", False)
        
        # Обновляем состояние
        await state.update_data(
            offers_page=new_page,
            offers_cursor=next_cursor,
            offers_has_next_page=has_next_page
        )
    else:
        # Если что-то пошло не так, просто возвращаем ошибку
        await callback_query.answer(
            "Невозможно перейти на запрошенную страницу."
        )
        return
    
    # Форматируем текст сообщения с результатами новой страницы
    results_text = format_offers_message(
        offers,
        new_page,
        10 if has_next_page else new_page  # Предполагаем макс. 10 страниц
    )
    
    # Создаем клавиатуру с кнопками навигации
    keyboard = create_pagination_keyboard(
        page=new_page,
        total_pages=10 if has_next_page else new_page,
        has_next_page=has_next_page,
        has_prev_page=new_page > 1
    )
    
    # Обновляем сообщение с результатами
    await callback_query.message.edit_text(
        results_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    # Отвечаем на callback
    await callback_query.answer()
    
    # Обновляем состояние
    await state.update_data(offers_page=new_page) 