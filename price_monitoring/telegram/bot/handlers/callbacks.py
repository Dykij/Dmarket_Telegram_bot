import logging
import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from ..keyboards import (
    create_main_menu_keyboard,
    create_mode_selection_keyboard,
    create_filter_settings_keyboard,
    create_game_selection_keyboard,
    create_pagination_keyboard
)
from ..formatters import format_offers_message
from ..states import FilterStates
# Assuming dmarket_api_client is correctly placed and importable
# from price_monitoring.parsers.dmarket_api import dmarket_api_client
from .filters import (
    game_callback_filter,
    mode_callback_filter,
    pagination_callback_filter
)

logger = logging.getLogger(__name__)
router = Router()
PAGE_SIZE = 5 # Consider moving to config

@router.callback_query(lambda c: c.data == "select_mode")
async def process_select_mode(callback_query: types.CallbackQuery):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    keyboard = create_mode_selection_keyboard()
    await callback_query.message.edit_text("\U0001F3AF Выберите режим работы:", reply_markup=keyboard)
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "configure_filters")
async def process_configure_filters(callback_query: types.CallbackQuery):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    keyboard = create_filter_settings_keyboard()
    await callback_query.message.edit_text(
        "🛠️ <b>Настройка фильтров</b>\n\n"
        "Выберите параметр для настройки:\n\n"
        "<i>Эти настройки будут использоваться для поиска выгодных предложений.</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "select_games")
async def process_select_games(callback_query: types.CallbackQuery):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
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
    await callback_query.answer()

@router.callback_query(game_callback_filter)
async def process_game_selection(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    if not callback_query.data:
        await callback_query.answer("Error: Missing callback data.")
        return
    from ..keyboards import SUPPORTED_GAMES
    selected_game = callback_query.data.split("_", 1)[1]
    user_id = callback_query.from_user.id if callback_query.from_user else "Unknown"
    game_emojis = {"cs2": "🔫", "dota2": "🧙‍♂️", "tf2": "🎩", "rust": "🏝️", "all": "✅"}
    game_emoji = game_emojis.get(selected_game, "🎮")
    if selected_game == "all":
        logger.info(f"User {user_id} selected all games.")
        await state.update_data(selected_games=SUPPORTED_GAMES)
        message_text = (
            f"{game_emoji} <b>Вы выбрали все игры</b>\n\n"
            f"Поиск будет осуществляться по всем поддерживаемым играм: "
            f"<b>{', '.join(SUPPORTED_GAMES)}</b>\n\n"
            f"<i>Для изменения выбора вернитесь в раздел выбора игр.</i>"
        )
        await callback_query.message.edit_text(message_text, parse_mode="HTML")
        await callback_query.answer("Выбраны все игры")
    else:
        proper_game_name = next((game for game in SUPPORTED_GAMES if game.lower() == selected_game), selected_game.upper())
        logger.info(f"User {user_id} selected game: {selected_game}")
        await state.update_data(selected_games=[proper_game_name])
        message_text = (
            f"{game_emoji} <b>Вы выбрали игру: {proper_game_name}</b>\n\n"
            f"Поиск будет осуществляться только по предметам этой игры.\n\n"
            f"<i>Для изменения выбора вернитесь в разделе выбора игр.</i>"
        )
        await callback_query.message.edit_text(message_text, parse_mode="HTML")
        await callback_query.answer(f"Выбрана игра {proper_game_name}")
    await asyncio.sleep(2)
    keyboard = create_main_menu_keyboard()
    await callback_query.message.edit_text("Главное меню:", reply_markup=keyboard)

@router.callback_query(mode_callback_filter)
async def process_mode_selection(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    if not callback_query.data:
        await callback_query.answer("Error: Missing callback data.")
        return
    from ..keyboards import TRADING_MODES
    selected_mode = callback_query.data.split("_", 1)[1]
    user_id = callback_query.from_user.id if callback_query.from_user else "Unknown"
    if selected_mode in TRADING_MODES:
        mode_info = TRADING_MODES[selected_mode]
        await state.update_data(
            selected_mode=selected_mode,
            min_profit=mode_info["min_profit"],
            max_profit=mode_info["max_profit"]
        )
        logger.info(f"User {user_id} selected trading mode: {mode_info['name']}")
        message_text = (
            f"{mode_info['emoji']} <b>Выбран режим: {mode_info['name']}</b>\n\n"
            f"<b>📋 Описание:</b>\n"
            f"{mode_info['description']}\n\n"
            f"<b>💰 Диапазон прибыли:</b> "
            f"${mode_info['min_profit']}-${mode_info['max_profit']}\n\n"
            f"✅ <i>Настройка сохранена. Теперь вы можете показать "
            f"предложения или настроить фильтры.</i>"
        )
        await callback_query.message.edit_text(message_text, parse_mode="HTML")
        await callback_query.answer("Режим успешно выбран!")
        await asyncio.sleep(2)
        keyboard = create_main_menu_keyboard()
        await callback_query.message.edit_text("Главное меню:", reply_markup=keyboard)
    else:
        logger.warning(f"User {user_id} selected unknown mode: {selected_mode}")
        await callback_query.message.edit_text("⚠️ Неизвестный режим. Пожалуйста, выберите из предложенных.")
        await callback_query.answer("Неизвестный режим")
        await asyncio.sleep(2)
        keyboard = create_main_menu_keyboard()
        await callback_query.message.edit_text("Главное меню:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "back_to_main_menu")
async def process_back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    current_state = await state.get_state()
    if current_state == FilterStates.browsing_offers:
        await state.clear()
    keyboard = create_main_menu_keyboard()
    await callback_query.message.edit_text("Главное меню:", reply_markup=keyboard)
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "show_offers")
async def process_show_offers(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    # --- Mock dmarket_api_client for now ---
    # This is a placeholder. Replace with actual API client import and call.
    class MockDMarketApiClient:
        async def find_arbitrage_opportunities(self, game, min_profit, max_profit, limit, cursor=None):
            # Simulate API call
            print(f"Mock API: Searching {game} profit ${min_profit}-${max_profit} limit {limit} cursor {cursor}")
            await asyncio.sleep(1)
            if cursor == "page_1": # Simulate second page
                return {
                    "items": [
                        {'game': game, 'name': f'Item {i+limit}', 'buy_price': 15.0, 'sell_price': 25.0, 'profit': 10.0} 
                        for i in range(limit)
                    ],
                    "cursor": None, # No more pages after this
                    "has_next_page": False
                }
            else: # Simulate first page
                return {
                    "items": [
                        {'game': game, 'name': f'Item {i}', 'buy_price': 10.0, 'sell_price': 20.0, 'profit': 10.0} 
                        for i in range(limit)
                    ],
                    "cursor": "page_1", # Cursor for next page
                    "has_next_page": True
                }
    dmarket_api_client = MockDMarketApiClient()
    # --- End Mock ---

    from ..keyboards import TRADING_MODES
    user_data = await state.get_data()
    selected_mode = user_data.get("selected_mode", "balance_boost")
    selected_games = user_data.get("selected_games", ["CS2"]) # Default to CS2
    min_profit = float(user_data.get("min_profit", TRADING_MODES.get(selected_mode, {}).get("min_profit", 1)))
    max_profit = float(user_data.get("max_profit", TRADING_MODES.get(selected_mode, {}).get("max_profit", 100)))
    
    mode_name = "не выбран"
    mode_emoji = "\U00002753"  # ❓
    if selected_mode in TRADING_MODES:
        mode_name = TRADING_MODES[selected_mode]["name"]
        mode_emoji = TRADING_MODES[selected_mode]["emoji"]
    
    games_str = ", ".join(selected_games) if selected_games else "не выбраны"
    
    search_game = "cs2" # Default search game
    if selected_games and len(selected_games) == 1:
        search_game = selected_games[0].lower()
    elif selected_games: # If multiple games selected, maybe default to cs2 or make it explicit? For now, using cs2.
        search_game = "cs2" 
        # Or perhaps indicate search across all selected? API needs to support this.

    message_text = (
        f"🔍 <b>Поиск выгодных предложений</b>\n\n"
        f"<b>Параметры поиска:</b>\n"
        f"{mode_emoji} <b>Режим:</b> {mode_name}\n"
        f"🎮 <b>Игры:</b> {games_str}\n"
        f"💰 <b>Прибыль:</b> от <b>${min_profit:.2f}</b> до <b>${max_profit:.2f}</b>\n\n"
        f"<i>Идет поиск предложений... это может занять некоторое время.</i>\n"
        f"<i>Результаты поиска будут отправлены отдельным сообщением.</i>"
    )
    await callback_query.message.edit_text(message_text, parse_mode="HTML")
    await callback_query.answer("Начат поиск предложений...")
    
    try:
        # Assume API only searches one game at a time for now
        search_result = await dmarket_api_client.find_arbitrage_opportunities(
            game=search_game, 
            min_profit=min_profit,
            max_profit=max_profit,
            limit=PAGE_SIZE
        )
        offers = search_result.get("items", [])
        cursor = search_result.get("cursor")
        has_next_page = search_result.get("has_next_page", False)
        
        total_pages_estimate = 10 if has_next_page else 1 # Placeholder for total pages
        
        await state.update_data(
            offers_page=1,
            offers_cursor=cursor,
            offers_game=search_game,
            offers_min_profit=min_profit,
            offers_max_profit=max_profit,
            offers_has_next_page=has_next_page,
            offers_total_pages=total_pages_estimate # Store estimated total
        )
        await state.set_state(FilterStates.browsing_offers)
        
        results_text = format_offers_message(offers, 1, total_pages_estimate)
        keyboard = create_pagination_keyboard(page=1, total_pages=total_pages_estimate, has_next_page=has_next_page, has_prev_page=False)
        
        # Send results in a new message
        await callback_query.message.answer(results_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error searching for offers: {e}", exc_info=True)
        error_keyboard = create_main_menu_keyboard()
        await callback_query.message.answer(
            "❌ <b>Ошибка при поиске предложений</b>\n\n"
            f"Произошла ошибка при поиске предложений:\n"
            f"<code>{str(e)}</code>\n\n"
            f"<i>Пожалуйста, попробуйте позже или обратитесь к администратору.</i>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )

@router.callback_query(pagination_callback_filter)
async def process_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    if not callback_query.data:
        await callback_query.answer("Error: Missing callback data.")
        return
        
    # --- Use Mock dmarket_api_client again ---
    class MockDMarketApiClient:
        async def find_arbitrage_opportunities(self, game, min_profit, max_profit, limit, cursor=None):
            print(f"Mock API Paginate: Searching {game} profit ${min_profit}-${max_profit} limit {limit} cursor {cursor}")
            await asyncio.sleep(0.5)
            if cursor == "page_1":
                return {
                    "items": [
                        {'game': game, 'name': f'Paginated Item {i+limit}', 'buy_price': 16.0, 'sell_price': 26.0, 'profit': 10.0} 
                        for i in range(limit)
                    ],
                    "cursor": "page_2", # Cursor for page 3
                    "has_next_page": True
                }
            elif cursor == "page_2": # Simulate third page
                 return {
                    "items": [
                        {'game': game, 'name': f'Paginated Item {i+limit*2}', 'buy_price': 17.0, 'sell_price': 27.0, 'profit': 10.0} 
                        for i in range(limit)
                    ],
                    "cursor": None, # No more pages
                    "has_next_page": False
                }
            else: # Should not happen in this mock if logic is correct
                 return {"items": [], "cursor": None, "has_next_page": False}
    dmarket_api_client = MockDMarketApiClient()
    # --- End Mock ---

    user_data = await state.get_data()
    current_page = user_data.get("offers_page", 1)
    cursor = user_data.get("offers_cursor")
    game = user_data.get("offers_game", "cs2")
    min_profit = user_data.get("offers_min_profit", 1.0)
    max_profit = user_data.get("offers_max_profit", 100.0)
    total_pages = user_data.get("offers_total_pages", 1) # Get stored total pages
    
    action = callback_query.data.split("_")[1]
    new_page = current_page
    search_cursor = None
    
    if action == "next" and cursor:
        new_page = current_page + 1
        search_cursor = cursor
    elif action == "prev" and current_page > 1:
        # Pagination logic for 'prev' is tricky without storing previous cursors.
        # For this example, we'll assume the API doesn't directly support going back.
        # A real implementation might need to re-fetch or store cursor history.
        await callback_query.answer("Функция 'Назад' по страницам пока не реализована.")
        return 
        # new_page = current_page - 1
        # # Need a way to get the cursor for the *previous* page. This often requires 
        # # storing cursor history or making the API support page numbers/offsets.
        # search_cursor = user_data.get(f"offers_cursor_page_{new_page}") # Example if storing history
    else:
        await callback_query.answer("Невозможно перейти на запрошенную страницу.")
        return

    if search_cursor is None and action != "prev": # Prevent search if no cursor for next page
        await callback_query.answer("Нет следующей страницы.")
        return
        
    try:
        await callback_query.answer("Загрузка...") # Provide feedback
        search_result = await dmarket_api_client.find_arbitrage_opportunities(
            game=game,
            min_profit=min_profit,
            max_profit=max_profit,
            limit=PAGE_SIZE,
            cursor=search_cursor
        )
        offers = search_result.get("items", [])
        next_cursor = search_result.get("cursor")
        has_next_page = search_result.get("has_next_page", False)
        
        # Update total pages estimate if we discover there's no next page earlier than expected
        if not has_next_page and total_pages > new_page:
            total_pages = new_page
            
        await state.update_data(
            offers_page=new_page,
            offers_cursor=next_cursor, # Store cursor for the *next* page
            offers_has_next_page=has_next_page,
            offers_total_pages=total_pages # Update total pages estimate
            # Consider storing previous cursors here if needed: f"offers_cursor_page_{new_page}": cursor
        )
        
        results_text = format_offers_message(offers, new_page, total_pages)
        keyboard = create_pagination_keyboard(page=new_page, total_pages=total_pages, has_next_page=has_next_page, has_prev_page=new_page > 1)
        
        await callback_query.message.edit_text(results_text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error during pagination: {e}", exc_info=True)
        await callback_query.answer("Ошибка при загрузке страницы.")
        # Optionally edit message to show error
        await callback_query.message.edit_text(
            "❌ Ошибка при загрузке страницы. Попробуйте вернуться в главное меню.",
            reply_markup=create_main_menu_keyboard()
        )


@router.callback_query(lambda c: c.data == "show_help")
async def process_show_help(callback_query: types.CallbackQuery):
    if not callback_query.message or not isinstance(callback_query.message, types.Message):
        await callback_query.answer("Cannot process: original message not found or inaccessible.")
        return
    # Reusing help text logic from commands.py for consistency is better
    # but for this example, duplicating it slightly modified for callback context
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
        "<b>Как пользоваться:</b>\n"
        "1. Выберите режим работы, соответствующий вашей стратегии\n"
        "2. Настройте фильтры для поиска (минимальная/максимальная прибыль)\n"
        "3. Выберите игру или все игры для поиска\n"
        "4. Нажмите 'Показать предложения' для поиска выгодных предметов\n"
        "5. Просматривайте результаты с помощью кнопок навигации\n\n"
        "<i>Для возврата в главное меню нажмите кнопку ниже.</i>"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder # Local import for clarity
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Вернуться в главное меню", callback_data="back_to_main_menu")
    keyboard = builder.as_markup()
    await callback_query.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")
    await callback_query.answer("Показана справка по боту") 