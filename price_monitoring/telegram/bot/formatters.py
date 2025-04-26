def format_offers_message(offers: list, page: int, total_pages: int) -> str:
    if not offers:
        return (
            "🚫 <b>Bbiroдhbix npeдлoжehuй he haйдeho</b>\n\n"
            "Пo 3aдahhbim napametpam he haйдeho npeдлoжehuй c npu6biл'ю.\n\n"
            "Пonpo6yйte u3mehut' napametpbi noucka uлu вbi6pat' дpyryю urpy."
        )

    message = f"💰 <b>Haйдehbi вbiroдhbie npeдлoжehuя</b> (ctp. {page}/{total_pages}):\n\n"

    game_emoji = {"cs2": "🔫", "dota2": "🧙‍♂️", "tf2": "🎩", "rust": "🏝️"}

    for item in offers:
        game_icon = game_emoji.get(item["game"].lower(), "🎮")
        profit = float(item["profit"])
        if profit >= 20:
            profit_indicator = "🔥"
        elif profit >= 10:
            profit_indicator = "💎"
        elif profit >= 5:
            profit_indicator = "📈"
        else:
            profit_indicator = "⚖️"

        buy_price = float(item["buy_price"])
        sell_price = float(item["sell_price"])
        profit_percent = (profit / buy_price) * 100 if buy_price > 0 else 0

        message += (
            f"<b>{game_icon} {item['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Цeha nokynku: <b>${buy_price:.2f}</b>\n"
            f"💸 Цeha npoдaжu: <b>${sell_price:.2f}</b>\n"
            f"{profit_indicator} Пpu6biл': <b>${profit:.2f}</b> "
            f"(<i>{profit_percent:.1f}%</i>)\n\n"
        )

    message += (
        "Иcnoл'3yйte khonku haвuraцuu для npocmotpa дpyrux npeдлoжehuй.\n"
        "<i>Цehbi yka3ahbi c yчetom komuccuu nлoщaдku.</i>"
    )
    return message
