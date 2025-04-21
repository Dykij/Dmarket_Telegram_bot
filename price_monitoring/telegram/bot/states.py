from aiogram.fsm.state import State, StatesGroup

class FilterStates(StatesGroup):
    waiting_min_profit = State()  # Ожидание ввода минимальной прибыли
    waiting_max_profit = State()  # Ожидание ввода максимальной прибыли
    browsing_offers = State()    # Просмотр предложений с пагинацией 