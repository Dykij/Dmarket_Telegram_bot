"""Kohctahtbi для peжumoв toproвлu в Telegram-6ote."""

# Peжumbi pa6otbi u ux hactpoйku
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

# Kohctahta для koлuчectвa элemehtoв ha ctpahuцe
PAGE_SIZE = 5
