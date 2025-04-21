from aiogram.types import InlineKeyboardMarkup

from price_monitoring.constants import SUPPORTED_GAMES, TRADING_MODES
from price_monitoring.telegram.bot.keyboards import (
    create_filter_settings_keyboard,
    create_game_selection_keyboard,
    create_main_menu_keyboard,
    create_mode_selection_keyboard,
    create_pagination_keyboard,
)


def test_create_main_menu_keyboard():
    """Тест создания клавиатуры главного меню."""
    keyboard = create_main_menu_keyboard()
   
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
   
    # Проверяем наличие кнопок
    buttons = keyboard.inline_keyboard
    assert len(buttons) >= 4  # Должно быть минимум 4 ряда кнопок
   
    # Проверяем наличие конкретных callback_data
    all_callback_data = [
        button.callback_data
        for row in buttons
        for button in row
    ]
   
    assert "show_offers" in all_callback_data
    assert "filter_settings" in all_callback_data
    assert "select_game" in all_callback_data
    assert "show_help" in all_callback_data


def test_create_game_selection_keyboard():
    """Тест создания клавиатуры выбора игры."""
    keyboard = create_game_selection_keyboard()
   
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
   
    # Проверяем наличие кнопок для всех поддерживаемых игр
    buttons = keyboard.inline_keyboard
    all_callback_data = [
        button.callback_data
        for row in buttons
        for button in row
    ]
   
    for game in SUPPORTED_GAMES:
        assert f"select_game:{game}" in all_callback_data


def test_create_filter_settings_keyboard():
    """Тест создания клавиатуры настроек фильтра."""
    keyboard = create_filter_settings_keyboard()
   
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
   
    # Проверяем наличие кнопок для настроек фильтра
    buttons = keyboard.inline_keyboard
    all_callback_data = [
        button.callback_data
        for row in buttons
        for button in row
    ]
   
    assert "set_min_price" in all_callback_data
    assert "set_limit" in all_callback_data
    assert "back_to_main" in all_callback_data


def test_create_mode_selection_keyboard():
    """Тест создания клавиатуры выбора режима торговли."""
    keyboard = create_mode_selection_keyboard()
   
    # Проверяем, что возвращается правильный тип
    assert isinstance(keyboard, InlineKeyboardMarkup)
   
    # Проверяем наличие кнопок для всех режимов торговли
    buttons = keyboard.inline_keyboard
    all_callback_data = [
        button.callback_data
        for row in buttons
        for button in row
    ]
   
    for mode in TRADING_MODES:
        assert f"select_mode:{mode}" in all_callback_data


def test_create_pagination_keyboard():
    """Тест создания клавиатуры пагинации."""
    # Тест для первой страницы
    first_page_kb = create_pagination_keyboard(
        current_page=1,
        total_pages=5
    )
    assert isinstance(first_page_kb, InlineKeyboardMarkup)
    first_buttons = first_page_kb.inline_keyboard
    first_callback_data = [
        btn.callback_data
        for row in first_buttons
        for btn in row
    ]
   
    assert "page:2" in first_callback_data  # Кнопка "Вперед"
    assert "page:0" not in first_callback_data
   
    # Тест для средней страницы
    middle_page_kb = create_pagination_keyboard(
        current_page=3,
        total_pages=5
    )
    assert isinstance(middle_page_kb, InlineKeyboardMarkup)
    middle_buttons = middle_page_kb.inline_keyboard
    middle_callback_data = [
        btn.callback_data
        for row in middle_buttons
        for btn in row
    ]
   
    assert "page:2" in middle_callback_data  # Кнопка "Назад"
    assert "page:4" in middle_callback_data  # Кнопка "Вперед"
   
    # Тест для последней страницы
    last_page_kb = create_pagination_keyboard(
        current_page=5,
        total_pages=5
    )
    assert isinstance(last_page_kb, InlineKeyboardMarkup)
    last_buttons = last_page_kb.inline_keyboard
    last_callback_data = [
        btn.callback_data
        for row in last_buttons
        for btn in row
    ]
   
    assert "page:4" in last_callback_data  # Кнопка "Назад"
    # Нет кнопки "Вперед" на последней странице
    assert "page:6" not in last_callback_data
