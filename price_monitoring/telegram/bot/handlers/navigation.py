"""Navigation and pagination handlers for the Telegram bot."""

import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from price_monitoring.telegram.bot.keyboards.pagination import (
    create_pagination_keyboard
)
from price_monitoring.telegram.bot.filters.callback_filters import (
    pagination_callback_filter
)
from price_monitoring.telegram.bot.utils.formatter import (
    format_offers_message
)
from price_monitoring.telegram.bot.states.filter_states import (
    FilterStates
)
from price_monitoring.telegram.bot.keyboards.main_menu import (
    create_main_menu_keyboard
)
from price_monitoring.telegram.bot.constants.trading_modes import (
    PAGE_SIZE
)
from price_monitoring.parsers.dmarket_api import dmarket_api_client

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(lambda c: c.data == "back_to_main_menu")
async def process_back_to_main_menu(
    callback_query: types.CallbackQuery, state: FSMContext
):
    """
    Обработчик нажатия на кнопку "Назад в главное меню".
    Возвращает пользователя в главное меню.
    
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
    
    # Проверяем текущее состояние
    current_state = await state.get_state()
    
    # Если мы в режиме просмотра предложений, сбрасываем состояние
    if current_state == FilterStates.browsing_offers:
        await state.clear()
    
    # Показываем главное меню
    keyboard = create_main_menu_keyboard()
    await callback_query.message.edit_text(
        "Главное меню:", reply_markup=keyboard
    )
    await callback_query.answer()


@router.callback_query(pagination_callback_filter)
async def process_pagination(
    callback_query: types.CallbackQuery, state: FSMContext
):
    """
    Обрабатывает нажатие на кнопки пагинации "Вперед" и "Назад".
    
    Получает следующую/предыдущую страницу результатов и обновляет
    сообщение с клавиатурой навигации.
    
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
        
        # Загружаем предыдущую страницу
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


@router.callback_query(lambda c: c.data == "show_help")
async def process_show_help(callback_query: types.CallbackQuery):
    """
    Обработчик нажатия на кнопку "Помощь".
    Показывает справку по использованию бота.
    
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
    
    # Создаем сообщение с подробной информацией о боте
    help_text = (
        "📚 <b>Помощь по использованию бота</b>\n\n"
        "<b>Основные возможности:</b>\n\n"
        "🔍 <b>Поиск выгодных предложений</b> - бот находит предметы "
        "на DMarket с наилучшим соотношением цены покупки и продажи.\n\n"
        "<b>🎮 Поддерживаемые игры:</b>\n"
        "• 🔫 CS2 (Counter-Strike 2)\n"
        "• 🧙‍♂️ Dota 2\n"
        "• 🎩 Team Fortress 2 (TF2)\n"
        "• 🏝️ Rust\n\n"
        "<b>Режимы работы:</b>\n"
        "• 💸 <b>Разгон баланса</b> - предметы с небольшой прибылью "
        "($1-5) и низким риском\n"
        "• 💰 <b>Средний трейдер</b> - предметы со средней прибылью ($5-20)\n"
        "• 📈 <b>Trade Pro</b> - редкие предметы с высокой прибылью ($20+)\n\n"
        "<b>Как пользоваться:</b>\n"
        "1. Выберите режим работы, соответствующий вашей стратегии\n"
        "2. Настройте фильтры для поиска (минимальная/максимальная прибыль)\n"
        "3. Выберите игру или все игры для поиска\n"
        "4. Нажмите 'Показать предложения' для поиска выгодных предметов\n"
        "5. Просматривайте результаты с помощью кнопок навигации\n\n"
        "<i>Для возврата в главное меню нажмите кнопку ниже.</i>"
    )
    
    # Создаем клавиатуру с кнопкой для возврата в главное меню
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ Вернуться в главное меню",
        callback_data="back_to_main_menu"
    )
    keyboard = builder.as_markup()  # type: ignore
    
    # Редактируем текущее сообщение, показывая справку
    await callback_query.message.edit_text(
        help_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Отвечаем на callback
    await callback_query.answer("Показана справка по боту") 