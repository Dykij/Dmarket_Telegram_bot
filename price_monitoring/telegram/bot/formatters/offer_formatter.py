"""Formatters for offer messages in the Telegram bot."""

from typing import List, Dict, Any


def format_offers_message(
    offers: List[Dict[str, Any]], 
    page: int, 
    total_pages: int
) -> str:
    """
    Форматирует список предложений в текстовое сообщение.
    
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