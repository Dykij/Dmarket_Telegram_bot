import pytest
from price_monitoring.telegram.bot.formatters import format_offers_message


def test_format_offers_message_empty():
    """Проверяет форматирование сообщения при отсутствии предложений."""
    message = format_offers_message([], 1, 1)
    
    # Проверяем, что в сообщении есть текст о том, что предложения не найдены
    assert "Выгодных предложений не найдено" in message
    assert "Попробуйте изменить параметры поиска" in message


def test_format_offers_message_with_offers():
    """Проверяет форматирование сообщения с предложениями."""
    # Создаем тестовые данные
    offers = [
        {
            'game': 'cs2',
            'name': 'Test Item 1',
            'buy_price': 10.0,
            'sell_price': 15.0,
            'profit': 5.0
        },
        {
            'game': 'dota2',
            'name': 'Test Item 2',
            'buy_price': 20.0,
            'sell_price': 40.0,
            'profit': 20.0
        }
    ]
    
    message = format_offers_message(offers, 1, 2)
    
    # Проверяем наличие общего заголовка
    assert "Найдены выгодные предложения" in message
    assert "(стр. 1/2)" in message
    
    # Проверяем наличие данных обоих предметов
    assert "Test Item 1" in message
    assert "Test Item 2" in message
    
    # Проверяем наличие цен
    assert "$10.00" in message
    assert "$15.00" in message
    assert "$20.00" in message
    assert "$40.00" in message
    
    # Проверяем наличие прибыли
    assert "$5.00" in message
    assert "$20.00" in message
    
    # Проверяем наличие процентов прибыли
    assert "50.0%" in message  # 5.0 / 10.0 * 100
    assert "100.0%" in message  # 20.0 / 20.0 * 100
    
    # Проверяем наличие иконок игр
    assert "🔫" in message  # CS2
    assert "🧙‍♂️" in message  # Dota2
    
    # Проверяем наличие инструкций по навигации
    assert "Используйте кнопки навигации" in message


def test_format_offers_message_profit_indicators():
    """Проверяет правильность отображения индикаторов прибыли."""
    low_profit_item = {
        'game': 'cs2',
        'name': 'Low Profit Item',
        'buy_price': 10.0,
        'sell_price': 12.0,
        'profit': 2.0
    }
    
    medium_profit_item = {
        'game': 'cs2',
        'name': 'Medium Profit Item',
        'buy_price': 10.0,
        'sell_price': 16.0,
        'profit': 6.0
    }
    
    high_profit_item = {
        'game': 'cs2',
        'name': 'High Profit Item',
        'buy_price': 10.0,
        'sell_price': 25.0,
        'profit': 15.0
    }
    
    very_high_profit_item = {
        'game': 'cs2',
        'name': 'Very High Profit Item',
        'buy_price': 10.0,
        'sell_price': 40.0,
        'profit': 30.0
    }
    
    # Проверяем индикаторы для каждого уровня прибыли
    low_message = format_offers_message([low_profit_item], 1, 1)
    medium_message = format_offers_message([medium_profit_item], 1, 1)
    high_message = format_offers_message([high_profit_item], 1, 1)
    very_high_message = format_offers_message([very_high_profit_item], 1, 1)
    
    # Индикатор для низкой прибыли (< 5)
    assert "⚖️" in low_message
    
    # Индикатор для средней прибыли (>= 5 и < 10)
    assert "📈" in medium_message
    
    # Индикатор для высокой прибыли (>= 10 и < 20)
    assert "💎" in high_message
    
    # Индикатор для очень высокой прибыли (>= 20)
    assert "🔥" in very_high_message


def test_format_offers_message_unknown_game():
    """Проверяет обработку неизвестной игры."""
    # Создаем тестовые данные с неизвестной игрой
    offer = {
        'game': 'unknown_game',
        'name': 'Unknown Game Item',
        'buy_price': 10.0,
        'sell_price': 15.0,
        'profit': 5.0
    }
    
    message = format_offers_message([offer], 1, 1)
    
    # Проверяем, что используется стандартная иконка для неизвестной игры
    assert "🎮" in message
    assert "Unknown Game Item" in message 