"""Handler modules for the Telegram bot."""

# Необходимые импорты для корректной работы router.py
from . import commands  # noqa: F401
from . import callbacks  # noqa: F401
from . import states  # noqa: F401
from . import filters  # noqa: F401

# Старые импорты, которые пока сохраняем для обратной совместимости
from . import start  # noqa: F401
from . import mode  # noqa: F401
from . import game  # noqa: F401
from . import offers  # noqa: F401
from . import navigation  # noqa: F401

# Initialize handlers package 