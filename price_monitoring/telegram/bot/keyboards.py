from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Kohctahtbi для urp u peжumoв
SUPPORTED_GAMES = ["CS2", "Dota2", "TF2", "Rust"]

TRADING_MODES = {
    "balance_boost": {
        "name": "Pa3roh 6aлahca",
        "min_profit": 1,
        "max_profit": 5,
        "description": ("Пouck npeдmetoв c he6oл'шoй npu6biл'ю ($1-5) u hu3kum puckom"),
        "emoji": "\U0001f4b8",  # 💸
    },
    "medium_trader": {
        "name": "Cpeдhuй tpeйдep",
        "min_profit": 5,
        "max_profit": 20,
        "description": (
            "Фokyc ha npeдmetax co cpeдheй npu6biл'ю ($5-20), npuoputet лukвuдhbim npeдmetam"
        ),
        "emoji": "\U0001f4b0",  # 💰
    },
    "trade_pro": {
        "name": "Trade Pro",
        "min_profit": 20,
        "max_profit": 100,
        "description": ("Пouck peдkux npeдmetoв c вbicokoй npu6biл'ю ($20-100) u ahaлu3 tpehдoв"),
        "emoji": "\U0001f4c8",  # 📈
    },
}


def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Bbi6pat' peжum", callback_data="select_mode")
    builder.button(text="⚙️ Hactpout' фuл'tpbi", callback_data="configure_filters")
    builder.button(text="🔍 Пoka3at' npeдлoжehuя", callback_data="show_offers")
    builder.button(text="🎮 Bbi6pat' urpbi", callback_data="select_games")
    builder.button(text="❓ Пomoщ'", callback_data="show_help")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def create_game_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    game_emojis = {"CS2": "🔫", "Dota2": "🧙‍♂️", "TF2": "🎩", "Rust": "🏝️"}
    for game in SUPPORTED_GAMES:
        emoji = game_emojis.get(game, "🎮")
        builder.button(text=f"{emoji} {game}", callback_data=f"game_{game.lower()}")
    builder.button(text="✅ Bce urpbi", callback_data="game_all")
    builder.button(text="⬅️ Ha3aд", callback_data="back_to_main_menu")
    builder.adjust(2)
    return builder.as_markup()


def create_filter_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Yctahoвut' muh. npu6biл'", callback_data="filter_set_min_profit")
    builder.button(text="💸 Yctahoвut' makc. npu6biл'", callback_data="filter_set_max_profit")
    builder.button(text="⬅️ Ha3aд в rлaвhoe mehю", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_mode_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mode_id, mode_info in TRADING_MODES.items():
        builder.button(
            text=f"{mode_info['emoji']} {mode_info['name']}", callback_data=f"mode_{mode_id}"
        )
    builder.button(text="⬅️ Ha3aд", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_pagination_keyboard(
    page: int, total_pages: int, has_next_page: bool, has_prev_page: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_prev_page:
        builder.button(text="⬅️ Ha3aд", callback_data=f"page_prev_{page}")
    builder.button(text=f"📄 {page}/{total_pages}", callback_data="page_info")
    if has_next_page:
        builder.button(text="Bnepeд ➡️", callback_data=f"page_next_{page}")
    builder.button(text="⬅️ B rлaвhoe mehю", callback_data="back_to_main_menu")
    builder.adjust(3, 1)
    return builder.as_markup()
