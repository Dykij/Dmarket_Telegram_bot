import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram import types
from aiogram.fsm.context import FSMContext

from price_monitoring.telegram.bot.handlers.states import (
    process_set_min_profit,
    process_min_profit_value,
    process_max_profit_value
)
from price_monitoring.telegram.bot.states import FilterStates


@pytest.fixture
def callback_query_mock():
    """Mock for callback query with message."""
    message_mock = AsyncMock(spec=types.Message)
    message_mock.edit_text = AsyncMock()
    message_mock.reply = AsyncMock()
    
    callback_mock = AsyncMock(spec=types.CallbackQuery)
    callback_mock.message = message_mock
    callback_mock.answer = AsyncMock()
    callback_mock.data = "filter_set_min_profit"
    
    return callback_mock


@pytest.fixture
def message_mock():
    """Mock for message with reply method."""
    message = AsyncMock(spec=types.Message)
    message.reply = AsyncMock()
    message.text = "5"
    message.from_user = MagicMock()
    message.from_user.id = 12345
    return message


@pytest.fixture
def state_mock():
    """Mock for FSMContext."""
    state = AsyncMock(spec=FSMContext)
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={"min_profit": 2.0})
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    return state


async def test_process_set_min_profit(callback_query_mock, state_mock):
    """Test setting min profit state and message updates."""
    await process_set_min_profit(callback_query_mock, state_mock)
    
    # Check if state was set correctly
    state_mock.set_state.assert_called_once_with(
        FilterStates.waiting_min_profit
    )
    
    # Check if message was edited
    callback_query_mock.message.edit_text.assert_called_once()
    edit_text_args = callback_query_mock.message.edit_text.call_args[0][0]
    
    # Verify text content
    assert "Установка минимальной прибыли" in edit_text_args
    assert "Введите минимальное значение прибыли" in edit_text_args
    
    # Check if callback was answered
    callback_query_mock.answer.assert_called_once()


async def test_process_min_profit_value_valid(message_mock, state_mock):
    """Test processing valid min profit input."""
    # Set valid input
    message_mock.text = "5.5"
    
    # Patch the create_filter_settings_keyboard function
    with patch(
        "price_monitoring.telegram.bot.handlers.states"
        ".create_filter_settings_keyboard"
    ) as mock_keyboard:
        mock_keyboard.return_value = MagicMock()
        
        # Patch asyncio.sleep to avoid waiting
        with patch("asyncio.sleep", AsyncMock()):
            await process_min_profit_value(message_mock, state_mock)
    
    # Check state updates
    state_mock.update_data.assert_called_once_with(min_profit=5.5)
    state_mock.clear.assert_called_once()
    
    # Check confirmation message
    assert message_mock.reply.call_count >= 1
    confirm_message_call = message_mock.reply.call_args_list[0]
    confirm_text = confirm_message_call[0][0]
    
    assert "Минимальная прибыль установлена: $5.50" in confirm_text


async def test_process_min_profit_value_invalid(message_mock, state_mock):
    """Test processing invalid min profit input."""
    # Set invalid input
    message_mock.text = "not_a_number"
    
    await process_min_profit_value(message_mock, state_mock)
    
    # Check error message
    message_mock.reply.assert_called_once()
    error_message = message_mock.reply.call_args[0][0]
    assert "Пожалуйста, введите число" in error_message
    
    # Ensure state was not updated or cleared
    state_mock.update_data.assert_not_called()
    state_mock.clear.assert_not_called()


async def test_process_max_profit_value_valid(message_mock, state_mock):
    """Test processing valid max profit input."""
    message_mock.text = "10"
    
    # Patch the create_filter_settings_keyboard function
    with patch(
        "price_monitoring.telegram.bot.handlers.states"
        ".create_filter_settings_keyboard"
    ) as mock_keyboard:
        mock_keyboard.return_value = MagicMock()
        
        # Patch asyncio.sleep to avoid waiting
        with patch("asyncio.sleep", AsyncMock()):
            await process_max_profit_value(message_mock, state_mock)
    
    # Check state updates
    state_mock.update_data.assert_called_once_with(max_profit=10.0)
    state_mock.clear.assert_called_once()
    
    # Check confirmation message
    assert message_mock.reply.call_count >= 1
    confirm_message_call = message_mock.reply.call_args_list[0]
    confirm_text = confirm_message_call[0][0]
    
    assert "Максимальная прибыль установлена: $10.00" in confirm_text
    assert "от $2.00 до $10.00" in confirm_text


async def test_process_max_profit_lower_than_min(message_mock, state_mock):
    """Test setting max profit lower than min profit."""
    message_mock.text = "1.0"  # Lower than min_profit=2.0 from fixture
    
    await process_max_profit_value(message_mock, state_mock)
    
    # Check error message
    message_mock.reply.assert_called_once()
    error_message = message_mock.reply.call_args[0][0]
    expected_error = "Максимальная прибыль должна быть больше минимальной"
    assert expected_error in error_message
    
    # Ensure state was not updated or cleared
    state_mock.update_data.assert_not_called()
    state_mock.clear.assert_not_called()