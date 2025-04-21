"""Клавиатура пагинации для Telegram-бота."""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_pagination_keyboard(
    page: int, 
    total_pages: int,
    has_next_page: bool, 
    has_prev_page: bool
) -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками навигации для пагинации результатов.
    
    Args:
        page: Текущая страница
        total_pages: Общее количество страниц
        has_next_page: Флаг наличия следующей страницы
        has_prev_page: Флаг наличия предыдущей страницы
        
    Returns:
        Клавиатура с кнопками навигации
    """
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки навигации, если они нужны
    if has_prev_page:
        builder.button(
            text="⬅️ Назад", 
            callback_data=f"page_prev_{page}"
        )
    
    # Показываем текущую страницу и общее количество
    builder.button(
        text=f"📄 {page}/{total_pages}",
        callback_data="page_info"  # Этот callback не будет обрабатываться
    )
    
    if has_next_page:
        builder.button(
            text="Вперед ➡️", 
            callback_data=f"page_next_{page}"
        )
    
    # Кнопка возврата в главное меню
    builder.button(
        text="⬅️ В главное меню",
        callback_data="back_to_main_menu"
    )
    
    # Расположение кнопок: навигация в одном ряду, возврат - в другом
    builder.adjust(3, 1)
    return builder.as_markup() 