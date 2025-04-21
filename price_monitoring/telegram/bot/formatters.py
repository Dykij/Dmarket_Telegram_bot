def format_offers_message(offers: list, page: int, total_pages: int) -> str:
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
    
    game_emoji = {
        "cs2": "🔫",
        "dota2": "🧙‍♂️",
        "tf2": "🎩",
        "rust": "🏝️"
    }
    
    for item in offers:
        game_icon = game_emoji.get(item['game'].lower(), "🎮")
        profit = float(item['profit'])
        if profit >= 20:
            profit_indicator = "🔥"
        elif profit >= 10:
            profit_indicator = "💎"
        elif profit >= 5:
            profit_indicator = "📈"
        else:
            profit_indicator = "⚖️"
        
        buy_price = float(item['buy_price'])
        sell_price = float(item['sell_price'])
        profit_percent = (profit / buy_price) * 100 if buy_price > 0 else 0
        
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