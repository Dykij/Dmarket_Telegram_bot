import logging
import asyncio

from aiogram import Router, types
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from price_monitoring.parsers.dmarket_api import dmarket_api_client

logger = logging.getLogger(__name__)

router = Router()

# Константа для количества элементов на странице
PAGE_SIZE = 5


# Определение состояний FSM для настройки фильтров
class FilterStates(StatesGroup):
    waiting_min_profit = State()  # Ожидание ввода минимальной прибыли
    waiting_max_profit = State()  # Ожидание ввода максимальной прибыли
    browsing_offers = State()    # Просмотр предложений с пагинацией


def create_main_menu_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📊 Выбрать режим", callback_data="select_mode"
    )
    builder.button(
        text="⚙️ Настроить фильтры", callback_data="configure_filters"
    )
    builder.button(
        text="🔍 Показать предложения", callback_data="show_offers"
    )
    builder.button(
        text="🎮 Выбрать игры", callback_data="select_games"
    )
    builder.button(
        text="❓ Помощь", callback_data="show_help"
    )
    builder.adjust(2, 2, 1)  # Расположим кнопки: 2 в ряд, 2 в ряд, последнюю отдельно
    return builder.as_markup()


# Список поддерживаемых игр
SUPPORTED_GAMES = ["CS2", "Dota2", "TF2", "Rust"]


# Режимы работы и их настройки
TRADING_MODES = {
    "balance_boost": {
        "name": "Разгон баланса",
        "min_profit": 1,
        "max_profit": 5,
        "description": (
            "Поиск предметов с небольшой прибылью ($1-5) "
            "и низким риском"
        ),
        "emoji": "\U0001F4B8"  # 💸
    },
    "medium_trader": {
        "name": "Средний трейдер",
        "min_profit": 5,
        "max_profit": 20,
        "description": (
            "Фокус на предметах со средней прибылью ($5-20), "
            "приоритет ликвидным предметам"
        ),
        "emoji": "\U0001F4B0"  # 💰
    },
    "trade_pro": {
        "name": "Trade Pro",
        "min_profit": 20,
        "max_profit": 100,
        "description": (
            "Поиск редких предметов с высокой прибылью ($20-100) "
            "и анализ трендов"
        ),
        "emoji": "\U0001F4C8"  # 📈
    }
}


def create_game_selection_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Game emoji mapping
    game_emojis = {
        "CS2": "🔫",
        "Dota2": "🧙‍♂️",
        "TF2": "🎩",
        "Rust": "🏝️"
    }
    
    for game in SUPPORTED_GAMES:
        # Get emoji for the game
        emoji = game_emojis.get(game, "🎮")
        # Используем префикс game_ для callback_data
        builder.button(text=f"{emoji} {game}", callback_data=f"game_{game.lower()}")
    # Кнопка для выбора всех игр
    builder.button(text="✅ Все игры", callback_data="game_all")
    # Кнопка Назад в главное меню
    builder.button(text="⬅️ Назад", callback_data="back_to_main_menu")
    builder.adjust(2)  # По 2 кнопки в ряд
    return builder.as_markup()


# Функция для создания клавиатуры настройки фильтров
def create_filter_settings_keyboard() -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру для меню настройки фильтров.
    
    Returns:
        Клавиатура с кнопками настройки фильтров
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💵 Установить мин. прибыль", 
        callback_data="filter_set_min_profit"
    )
    builder.button(
        text="💸 Установить макс. прибыль", 
        callback_data="filter_set_max_profit"
    )
    builder.button(
        text="⬅️ Назад в главное меню",
        callback_data="back_to_main_menu"
    )
    builder.adjust(1)  # По одной кнопке в строке
    return builder.as_markup()


def create_mode_selection_keyboard() -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для выбора режима работы бота."""
    builder = InlineKeyboardBuilder()
    
    for mode_id, mode_info in TRADING_MODES.items():
        builder.button(
            text=f"{mode_info['emoji']} {mode_info['name']}",
            callback_data=f"mode_{mode_id}"
        )
    
    # Кнопка "Назад" в главное меню
    builder.button(
        text="⬅️ Назад",
        callback_data="back_to_main_menu"
    )
    
    # Размещаем кнопки по одной в строке для лучшей читаемости
    builder.adjust(1)
    return builder.as_markup()


@router.message(CommandStart())
async def handle_start(message: types.Message):
    # Проверка, что сообщение и пользователь существуют
    if not message.from_user:
        logger.warning("Received /start command without user info.")
        return

    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot.")
    keyboard = create_main_menu_keyboard()
    
    # Создаем приветственное сообщение с форматированием
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
    
    await message.answer(
        welcome_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def handle_help(message: types.Message):
    """
    Обработчик команды /help.
    Отправляет подробную информацию о возможностях бота и инструкции по использованию.
    """
    # Создаем сообщение с подробной информацией о боте
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
    
    # Создаем клавиатуру с кнопкой для возврата в главное меню
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ Вернуться в главное меню",
        callback_data="back_to_main_menu"
    )
    keyboard = builder.as_markup()
    
    # Отправляем справку
    await message.answer(
        help_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# Здесь будут обработчики для callback_query кнопок
@router.callback_query(lambda c: c.data == "select_mode")
async def process_select_mode(callback_query: types.CallbackQuery):
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


@router.callback_query(lambda c: c.data == "configure_filters")
async def process_configure_filters(callback_query: types.CallbackQuery):
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
        "<i>Эти настройки будут использоваться для поиска выгодных предложений.</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "show_offers")
async def process_show_offers(
    callback_query: types.CallbackQuery, state: FSMContext
):
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
        mode_name = TRADING_MODES[selected_mode]["name"]
        mode_emoji = TRADING_MODES[selected_mode]["emoji"]
    
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
        f"💰 <b>Прибыль:</b> от <b>${min_profit:.2f}</b> до <b>${max_profit:.2f}</b>\n\n"
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
        # Теперь ожидаем словарь с курсором для пагинации
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
        results_text = format_offers_message(offers, 1, 10 if has_next_page else 1)
        
        # Создаем клавиатуру с кнопками навигации
        keyboard = create_pagination_keyboard(
            page=1,
            total_pages=10 if has_next_page else 1,  # Предполагаем макс. 10 страниц для примера
            has_next_page=has_next_page,
            has_prev_page=False  # На первой странице нет предыдущей
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
            f"<i>Пожалуйста, попробуйте позже или обратитесь к администратору.</i>",
            parse_mode="HTML",
            reply_markup=create_main_menu_keyboard()
        )


@router.callback_query(lambda c: c.data == "select_games")
async def process_select_games(callback_query: types.CallbackQuery):
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


# Фильтр для callback_query, начинающихся с 'game_'
def game_callback_filter(callback: types.CallbackQuery) -> bool:
    return callback.data is not None and callback.data.startswith("game_")


# Фильтр для callback_query, начинающихся с 'mode_'
def mode_callback_filter(callback: types.CallbackQuery) -> bool:
    return callback.data is not None and callback.data.startswith("mode_")


# Фильтр для callback_query, связанных с фильтрами
def filter_callback_filter(callback: types.CallbackQuery) -> bool:
    return callback.data is not None and callback.data.startswith("filter_")


# Фильтр для callback_query, связанных с пагинацией
def pagination_callback_filter(callback: types.CallbackQuery) -> bool:
    return (callback.data is not None and 
            (callback.data.startswith("page_next_") or 
             callback.data.startswith("page_prev_")))


# Обработчик выбора конкретной игры или всех игр
# Используем именованный фильтр вместо lambda
@router.callback_query(game_callback_filter)
async def process_game_selection(
    callback_query: types.CallbackQuery, state: FSMContext
):
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

    # Game emoji mapping для отображения
    game_emojis = {
        "cs2": "🔫",
        "dota2": "🧙‍♂️",
        "tf2": "🎩",
        "rust": "🏝️",
        "all": "✅"
    }
    
    # Получаем emoji для выбранной игры
    game_emoji = game_emojis.get(selected_game, "🎮")

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
            (game for game in SUPPORTED_GAMES if game.lower() == selected_game),
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
    
    # Возвращаемся в главное меню путем редактирования текущего сообщения
    keyboard = create_main_menu_keyboard()
    await callback_query.message.edit_text(
        "Главное меню:",
        reply_markup=keyboard
    )


@router.callback_query(mode_callback_filter)
async def process_mode_selection(
    callback_query: types.CallbackQuery, state: FSMContext
):
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


@router.callback_query(lambda c: c.data == "back_to_main_menu")
async def process_back_to_main_menu(
    callback_query: types.CallbackQuery, state: FSMContext
):
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


@router.callback_query(lambda c: c.data == "filter_set_min_profit")
async def process_set_min_profit(
    callback_query: types.CallbackQuery, state: FSMContext
):
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
            "Вы можете продолжить настройку фильтров или вернуться в главное меню:",
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
            f"только предметы с прибылью от ${min_profit:.2f} до ${max_profit:.2f}.",
            parse_mode="HTML"
        )
        
        # Небольшая задержка перед возвратом в меню фильтров
        await asyncio.sleep(2)
        
        # Возвращаемся в меню фильтров
        keyboard = create_filter_settings_keyboard()
        
        await confirm_message.reply(
            "🛠️ <b>Вернуться к настройке фильтров?</b>\n\n"
            "Вы можете продолжить настройку фильтров или вернуться в главное меню:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except ValueError:
        await message.reply(
            "❌ Пожалуйста, введите число. Например: 20 или 25.5"
        )


# Создание клавиатуры для пагинации результатов
def create_pagination_keyboard(
    page: int, 
    total_pages: int,
    has_next_page: bool, 
    has_prev_page: bool
) -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками навигации для пагинации результатов.
    
    Args:
        page: Текущая страница
        total_pages: Общее количество страниц
        has_next_page: Флаг наличия следующей страницы
        has_prev_page: Флаг наличия предыдущей страницы
        
    Returns:
        Клавиатура с кнопками навигации
    """
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки навигации, если они нужны
    if has_prev_page:
        builder.button(
            text="⬅️ Назад", 
            callback_data=f"page_prev_{page}"
        )
    
    # Показываем текущую страницу и общее количество
    builder.button(
        text=f"📄 {page}/{total_pages}",
        callback_data="page_info"  # Этот callback не будет обрабатываться
    )
    
    if has_next_page:
        builder.button(
            text="Вперед ➡️", 
            callback_data=f"page_next_{page}"
        )
    
    # Кнопка возврата в главное меню
    builder.button(
        text="⬅️ В главное меню",
        callback_data="back_to_main_menu"
    )
    
    # Расположение кнопок: навигация в одном ряду, возврат - в другом
    builder.adjust(3, 1)
    return builder.as_markup()


# Функция для форматирования списка предложений в текстовое сообщение
def format_offers_message(
    offers: list, 
    page: int, 
    total_pages: int
) -> str:
    """
    Форматирует список предложений в текстовое сообщение с улучшенным форматированием.
    
    Args:
        offers: Список предложений для отображения
        page: Текущая страница
        total_pages: Общее количество страниц
        
    Returns:
        Отформатированное сообщение с предложениями
    """
    if not offers:
        return (
            "🚫 <b>Выгодных предложений не найдено</b>\n\n"
            "По заданным параметрам не найдено предложений с прибылью.\n\n"
            "Попробуйте изменить параметры поиска или выбрать другую игру."
        )
    
    message = (
        f"💰 <b>Найдены выгодные предложения</b> "
        f"(стр. {page}/{total_pages}):\n\n"
    )
    
    # Словарь соответствия игр и эмодзи
    game_emoji = {
        "cs2": "🔫",
        "dota2": "🧙‍♂️",
        "tf2": "🎩",
        "rust": "🏝️"
    }
    
    for item in offers:
        # Получаем эмодзи для игры
        game_icon = game_emoji.get(item['game'].lower(), "🎮")
        
        # Получаем эмодзи для индикации прибыльности
        profit = float(item['profit'])
        if profit >= 20:
            profit_indicator = "🔥"  # Высокая прибыль
        elif profit >= 10:
            profit_indicator = "💎"  # Хорошая прибыль
        elif profit >= 5:
            profit_indicator = "📈"  # Средняя прибыль
        else:
            profit_indicator = "⚖️"  # Низкая прибыль
        
        # Рассчитываем процент прибыли
        buy_price = float(item['buy_price'])
        sell_price = float(item['sell_price'])
        profit_percent = (profit / buy_price) * 100 if buy_price > 0 else 0
        
        # Форматируем карточку предмета
        message += (
            f"<b>{game_icon} {item['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Цена покупки: <b>${buy_price:.2f}</b>\n"
            f"💸 Цена продажи: <b>${sell_price:.2f}</b>\n"
            f"{profit_indicator} Прибыль: <b>${profit:.2f}</b> "
            f"(<i>{profit_percent:.1f}%</i>)\n\n"
        )
    
    message += (
        "Используйте кнопки навигации для просмотра других предложений.\n"
        "<i>Цены указаны с учетом комиссии площадки.</i>"
    )
    return message


# Обработчик для пагинации (кнопки Вперед/Назад)
@router.callback_query(pagination_callback_filter)
async def process_pagination(
    callback_query: types.CallbackQuery, state: FSMContext
):
    """
    Обрабатывает нажатие на кнопки пагинации "Вперед" и "Назад".
    
    Получает следующую/предыдущую страницу результатов и обновляет
    сообщение с клавиатурой навигации.
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
        
        # Имитация загрузки предыдущей страницы (в реальности нужен запрос к API)
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
        await callback_query.answer("Невозможно перейти на запрошенную страницу.")
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
    
    # Создаем клавиатуру с кнопкой для возврата в главное меню
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ Вернуться в главное меню",
        callback_data="back_to_main_menu"
    )
    keyboard = builder.as_markup()
    
    # Редактируем текущее сообщение, показывая справку
    await callback_query.message.edit_text(
        help_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Отвечаем на callback
    await callback_query.answer("Показана справка по боту") 