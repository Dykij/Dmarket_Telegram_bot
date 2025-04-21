import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext
from price_monitoring.telegram.bot.handlers.callbacks import (
    process_select_mode,
    process_back_to_main_menu,
    process_show_help
)


@pytest.fixture
def message_mock():
    """
    Создает мок объекта сообщения для тестирования.
    """
    message = MagicMock(spec=types.Message)
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def callback_query_mock(message_mock):
    """
    Создает мок объекта callback query для тестирования.
    """
    callback = MagicMock(spec=types.CallbackQuery)
    callback.message = message_mock
    callback.answer = AsyncMock()
    callback.data = "test_data"
    return callback


@pytest.fixture
def state_mock():
    """
    Создает мок объекта FSMContext для тестирования.
    """
    state = MagicMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=None)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state


@pytest.mark.asyncio
async def test_process_select_mode(callback_query_mock):
    """
    Тестирует обработчик выбора режима.
    """
    # Патчим функцию создания клавиатуры
    with patch(
        "price_monitoring.telegram.bot.handlers.callbacks.create_mode_selection_keyboard",
        return_value=MagicMock()
    ) as mock_keyboard:
        # Вызываем обработчик
        callback_query_mock.data = "select_mode"
        await process_select_mode(callback_query_mock)
        
        # Проверяем, что создание клавиатуры вызвано
        mock_keyboard.assert_called_once()
        
        # Проверяем, что edit_text вызван с правильными параметрами
        callback_query_mock.message.edit_text.assert_called_once()
        
        # Проверяем наличие текста "Выберите режим работы" в вызове edit_text
        args, kwargs = callback_query_mock.message.edit_text.call_args
        assert "режим" in args[0].lower()
        
        # Проверяем, что answer вызван
        callback_query_mock.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_back_to_main_menu(callback_query_mock, state_mock):
    """
    Тестирует обработчик возврата в главное меню.
    """
    # Патчим функцию создания клавиатуры
    with patch(
        "price_monitoring.telegram.bot.handlers.callbacks.create_main_menu_keyboard",
        return_value=MagicMock()
    ) as mock_keyboard:
        # Вызываем обработчик
        callback_query_mock.data = "back_to_main_menu"
        await process_back_to_main_menu(callback_query_mock, state_mock)
        
        # Проверяем, что создание клавиатуры вызвано
        mock_keyboard.assert_called_once()
        
        # Проверяем, что edit_text вызван с правильными параметрами
        callback_query_mock.message.edit_text.assert_called_once()
        
        # Проверяем, что answer вызван
        callback_query_mock.answer.assert_called_once()


@pytest.mark.asyncio
async def test_process_show_help(callback_query_mock):
    """
    Тестирует обработчик показа справки.
    """
    # Вызываем обработчик
    with patch(
        "aiogram.utils.keyboard.InlineKeyboardBuilder",
        return_value=MagicMock()
    ) as mock_builder:
        # Настраиваем мок для builder
        mock_builder.return_value.button = MagicMock()
        mock_builder.return_value.as_markup = MagicMock(return_value=MagicMock())
        
        # Вызываем обработчик
        callback_query_mock.data = "show_help"
        await process_show_help(callback_query_mock)
        
        # Проверяем, что edit_text вызван
        callback_query_mock.message.edit_text.assert_called_once()
        
        # Проверяем параметры вызова edit_text
        args, kwargs = callback_query_mock.message.edit_text.call_args
        # Проверяем, что текст содержит нужную информацию
        assert "Помощь" in args[0]
        assert "HTML" in kwargs.get("parse_mode", "")
        
        # Проверяем, что answer вызван с правильным сообщением
        callback_query_mock.answer.assert_called_once()
        args, _ = callback_query_mock.answer.call_args
        assert "справка" in args[0].lower() 