"""Фильтры для callback-запросов в Telegram-боте."""

from aiogram import types


def game_callback_filter(callback: types.CallbackQuery) -> bool:
    """
    Фильтр для callback_query с префиксом 'game_'.
    
    Args:
        callback: Callback query от Telegram
        
    Returns:
        True если callback_data начинается с 'game_', иначе False
    """
    return callback.data is not None and callback.data.startswith("game_")


def mode_callback_filter(callback: types.CallbackQuery) -> bool:
    """
    Фильтр для callback_query с префиксом 'mode_'.
    
    Args:
        callback: Callback query от Telegram
        
    Returns:
        True если callback_data начинается с 'mode_', иначе False
    """
    return callback.data is not None and callback.data.startswith("mode_")


def filter_callback_filter(callback: types.CallbackQuery) -> bool:
    """
    Фильтр для callback_query с префиксом 'filter_'.
    
    Args:
        callback: Callback query от Telegram
        
    Returns:
        True если callback_data начинается с 'filter_', иначе False
    """
    return callback.data is not None and callback.data.startswith("filter_")


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