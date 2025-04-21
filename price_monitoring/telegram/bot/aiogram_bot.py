import asyncio
import logging
from collections.abc import Iterable
from typing import Dict, List, Optional, Union

from aiogram import Bot, Dispatcher
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    InputMediaPhoto,
)

from ..models import InlineButton, ItemOfferNotification, NotificationType
from .abstract_bot import AbstractBot
from .abstract_command import AbstractCommand
from .abstract_whitelist import AbstractWhitelist

logger = logging.getLogger(__name__)


class AiogramBot(AbstractBot):
    """
    Реализация бота Telegram на основе библиотеки aiogram.

    Обеспечивает взаимодействие с API Telegram для отправки уведомлений
    и обработки команд от пользователей.

    Attributes:
        _whitelist: Объект для работы с белым списком пользователей
        commands: Список поддерживаемых команд
        _bot: Экземпляр класса Bot из aiogram
        _dispatcher: Экземпляр класса Dispatcher из aiogram
        _polling_task: Задача, представляющая процесс опроса серверов Telegram
    """

    def __init__(
        self,
        token: str,
        whitelist: AbstractWhitelist,
        commands: Iterable[AbstractCommand],
    ):
        """
        Инициализирует бота с указанным токеном и настройками.

        Args:
            token: Токен API Telegram
            whitelist: Объект для работы с белым списком пользователей
            commands: Список поддерживаемых команд
        """
        self._whitelist = whitelist
        self.commands = commands
        self._bot = Bot(token=token, parse_mode="HTML")
        self._dispatcher = Dispatcher()
        self._polling_task: Optional[asyncio.Task] = None

    async def start(self):
        """
        Запускает бота и начинает обработку входящих сообщений.

        Регистрирует все команды и запускает процесс опроса серверов
        Telegram.
        """
        members = await self._whitelist.get_members()
        for command in self.commands:
            command.register_command(self._dispatcher, members)
        self._polling_task = asyncio.create_task(
            # В aiogram 3.0 первый аргумент метода start_polling
            # должен быть экземпляром бота (позиционный аргумент, а не keyword)
            self._dispatcher.start_polling(self._bot)
        )

    async def notify(self, notification: ItemOfferNotification):
        """
        Отправляет уведомление всем пользователям из белого списка.

        Поддерживает различные типы уведомлений: текст, изображения, видео и т.д.
        Также поддерживает интерактивные кнопки для взаимодействия с пользователем.

        Args:
            notification: Объект уведомления для отправки
        """
        members = await self._whitelist.get_members()
        if not members:
            logger.warning("No members in whitelist to send notification to")
            return

        # Создаем клавиатуру, если есть кнопки
        reply_markup = None
        if notification.buttons or notification.button_rows:
            reply_markup = self._create_inline_keyboard(notification)

        tasks = []
        for chat_id in members:
            # Выбираем метод отправки в зависимости от типа уведомления
            task = asyncio.create_task(
                self._send_notification_by_type(chat_id, notification, reply_markup)
            )
            tasks.append(task)

        # Ждем завершения всех задач отправки
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Логируем результаты
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failure_count = len(results) - success_count

        if failure_count > 0:
            logger.warning(
                f"Failed to send notification to {failure_count} out of {len(members)} members"
            )

            # Логируем первые несколько ошибок
            error_count = 0
            for result in results:
                if isinstance(result, Exception) and error_count < 3:
                    logger.error(f"Error sending notification: {result}")
                    error_count += 1

    async def _send_notification_by_type(
        self, 
        chat_id: int, 
        notification: ItemOfferNotification,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ):
        """
        Отправляет уведомление конкретному пользователю в зависимости от типа.

        Args:
            chat_id: ID чата пользователя
            notification: Объект уведомления
            reply_markup: Клавиатура с кнопками (если есть)

        Returns:
            Результат отправки сообщения
        """
        try:
            if notification.notification_type == NotificationType.TEXT:
                # Отправляем текстовое сообщение
                return await self._bot.send_message(
                    chat_id=chat_id,
                    text=notification.text,
                    parse_mode="HTML",
                    disable_web_page_preview=not notification.preview_links,
                    reply_markup=reply_markup
                )

            elif notification.notification_type == NotificationType.IMAGE:
                # Проверяем наличие URL изображения
                if not notification.media_url:
                    logger.warning("Image notification without media_url, falling back to text")
                    return await self._bot.send_message(
                        chat_id=chat_id,
                        text=notification.text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )

                # Отправляем изображение
                caption = notification.caption or notification.text
                return await self._bot.send_photo(
                    chat_id=chat_id,
                    photo=notification.media_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )

            elif notification.notification_type == NotificationType.PHOTO_GROUP:
                # Проверяем наличие URL изображений
                if not notification.media_urls:
                    logger.warning("Photo group notification without media_urls, falling back to text")
                    return await self._bot.send_message(
                        chat_id=chat_id,
                        text=notification.text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )

                # Создаем группу изображений (максимум 10)
                media_group = []
                for i, url in enumerate(notification.media_urls[:10]):
                    # Добавляем подпись только к первому изображению
                    caption = notification.caption or notification.text if i == 0 else None
                    media_group.append(InputMediaPhoto(
                        media=url,
                        caption=caption,
                        parse_mode="HTML"
                    ))

                # Отправляем группу изображений
                await self._bot.send_media_group(
                    chat_id=chat_id,
                    media=media_group
                )

                # Если есть кнопки, отправляем их отдельным сообщением
                if reply_markup:
                    return await self._bot.send_message(
                        chat_id=chat_id,
                        text=notification.text or "Используйте кнопки ниже:",
                        reply_markup=reply_markup
                    )

            elif notification.notification_type == NotificationType.VIDEO:
                # Проверяем наличие URL видео
                if not notification.media_url:
                    logger.warning("Video notification without media_url, falling back to text")
                    return await self._bot.send_message(
                        chat_id=chat_id,
                        text=notification.text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )

                # Отправляем видео
                caption = notification.caption or notification.text
                return await self._bot.send_video(
                    chat_id=chat_id,
                    video=notification.media_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )

            elif notification.notification_type == NotificationType.ANIMATION:
                # Проверяем наличие URL анимации
                if not notification.media_url:
                    logger.warning("Animation notification without media_url, falling back to text")
                    return await self._bot.send_message(
                        chat_id=chat_id,
                        text=notification.text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )

                # Отправляем анимацию (GIF)
                caption = notification.caption or notification.text
                return await self._bot.send_animation(
                    chat_id=chat_id,
                    animation=notification.media_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )

            elif notification.notification_type == NotificationType.DOCUMENT:
                # Проверяем наличие URL документа
                if not notification.media_url:
                    logger.warning("Document notification without media_url, falling back to text")
                    return await self._bot.send_message(
                        chat_id=chat_id,
                        text=notification.text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )

                # Отправляем документ
                caption = notification.caption or notification.text
                return await self._bot.send_document(
                    chat_id=chat_id,
                    document=notification.media_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )

            else:
                # Неизвестный тип уведомления, отправляем как текст
                logger.warning(f"Unknown notification type: {notification.notification_type}")
                return await self._bot.send_message(
                    chat_id=chat_id,
                    text=notification.text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error(f"Error sending notification to {chat_id}: {e}")
            raise

    def _create_inline_keyboard(self, notification: ItemOfferNotification) -> InlineKeyboardMarkup:
        """
        Создает встроенную клавиатуру с кнопками для уведомления.

        Args:
            notification: Объект уведомления с кнопками

        Returns:
            Объект InlineKeyboardMarkup для отправки с сообщением
        """
        keyboard = InlineKeyboardMarkup(row_width=2)

        # Если есть отдельные кнопки, добавляем их
        if notification.buttons:
            for button in notification.buttons:
                keyboard_button = InlineKeyboardButton(
                    text=button.text,
                    callback_data=button.callback_data
                )
                if button.url:
                    keyboard_button = InlineKeyboardButton(
                        text=button.text,
                        url=button.url
                    )
                keyboard.add(keyboard_button)

        # Если есть ряды кнопок, добавляем их
        if notification.button_rows:
            for row in notification.button_rows:
                keyboard_row = []
                for button in row:
                    if button.url:
                        keyboard_row.append(InlineKeyboardButton(
                            text=button.text,
                            url=button.url
                        ))
                    else:
                        keyboard_row.append(InlineKeyboardButton(
                            text=button.text,
                            callback_data=button.callback_data
                        ))
                keyboard.row(*keyboard_row)

        return keyboard
