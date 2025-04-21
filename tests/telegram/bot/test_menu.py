import pytest
from unittest.mock import patch, MagicMock
from aiogram import Router

from price_monitoring.telegram.bot.menu import router


def test_menu_router_structure():
    """
    Проверяет, что центральный маршрутизатор правильно настроен.
    """
    # Проверяем, что router не None
    assert router is not None
    
    # Проверяем, что у роутера есть дочерние роутеры
    assert hasattr(router, 'sub_routers')
    
    # Проверяем, что список дочерних роутеров не пуст
    assert len(router.sub_routers) > 0
    
    # Проверяем количество включенных дочерних роутеров
    # (должно быть 3 - commands, callbacks, states)
    assert len(router.sub_routers) >= 3


@pytest.mark.asyncio
async def test_menu_router_initialization():
    """
    Проверяет инициализацию центрального маршрутизатора.
    """
    # Создаем фейковые роутеры
    mock_commands_router = Router()
    mock_callbacks_router = Router()
    mock_states_router = Router()
    
    # Создаем mock-логгер
    mock_logger = MagicMock()
    
    # Патчим все необходимые объекты
    patches = [
        patch('price_monitoring.telegram.bot.menu.logger', mock_logger),
        patch(
            'price_monitoring.telegram.bot.handlers.commands.router', 
            mock_commands_router
        ),
        patch(
            'price_monitoring.telegram.bot.handlers.callbacks.router', 
            mock_callbacks_router
        ),
        patch(
            'price_monitoring.telegram.bot.handlers.states.router', 
            mock_states_router
        )
    ]
    
    # Применяем все патчи
    for p in patches:
        p.start()
    
    try:
        # Импортируем модуль заново для повторной инициализации
        from importlib import reload
        import price_monitoring.telegram.bot.menu
        reload(price_monitoring.telegram.bot.menu)
        
        # Проверяем, что логгер был вызван с сообщением
        mock_logger.info.assert_called_once_with(
            "Main menu router successfully initialized"
        )
    finally:
        # Останавливаем все патчи
        for p in patches:
            p.stop() 