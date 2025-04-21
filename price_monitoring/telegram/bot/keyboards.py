from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

# Константы для игр и режимов
SUPPORTED_GAMES = ["CS2", "Dota2", "TF2", "Rust"]

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

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Выбрать режим", callback_data="select_mode")
    builder.button(
        text="⚙️ Настроить фильтры", 
        callback_data="configure_filters"
    )
    builder.button(
        text="🔍 Показать предложения", 
        callback_data="show_offers"
    )
    builder.button(text="🎮 Выбрать игры", callback_data="select_games")
    builder.button(text="❓ Помощь", callback_data="show_help")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def create_game_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    game_emojis = {"CS2": "🔫", "Dota2": "🧙‍♂️", "TF2": "🎩", "Rust": "🏝️"}
    for game in SUPPORTED_GAMES:
        emoji = game_emojis.get(game, "🎮")
        builder.button(
            text=f"{emoji} {game}", 
            callback_data=f"game_{game.lower()}"
        )
    builder.button(text="✅ Все игры", callback_data="game_all")
    builder.button(text="⬅️ Назад", callback_data="back_to_main_menu")
    builder.adjust(2)
    return builder.as_markup()

def create_filter_settings_keyboard() -> InlineKeyboardMarkup:
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
    builder.adjust(1)
    return builder.as_markup()

def create_mode_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mode_id, mode_info in TRADING_MODES.items():
        builder.button(
            text=f"{mode_info['emoji']} {mode_info['name']}", 
            callback_data=f"mode_{mode_id}"
        )
    builder.button(text="⬅️ Назад", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()

def create_pagination_keyboard(
    page: int, total_pages: int, has_next_page: bool, has_prev_page: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_prev_page:
        builder.button(text="⬅️ Назад", callback_data=f"page_prev_{page}")
    builder.button(text=f"📄 {page}/{total_pages}", callback_data="page_info")
    if has_next_page:
        builder.button(text="Вперед ➡️", callback_data=f"page_next_{page}")
    builder.button(text="⬅️ В главное меню", callback_data="back_to_main_menu")
    builder.adjust(3, 1)
    return builder.as_markup() 