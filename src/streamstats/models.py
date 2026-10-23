from collections.abc import Mapping  # подпись: «набор пар имя-значение»
from dataclasses import dataclass  # наклейка для «анкет» с данными
from datetime import UTC, datetime  # дата-время и часовой пояс
from enum import StrEnum  # список разрешённых значений
from typing import Any  # «что угодно», для подписи

from .errors import InvalidEventError, InvalidTimestampError  # наши ошибки

REQUIRED_FIELDS = ("timestamp", "level", "source", "message")  # обязательные графы


class Level(StrEnum):  # допустимые уровни
    DEBUG = "DEBUG"  # слева имя в коде, справа текст из файла
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)  # «анкета»: не меняется, занимает мало памяти
class Event:  # одно событие из файла
    timestamp: datetime  # когда
    level: Level  # какой уровень
    source: str  # откуда
    message: str  # что случилось


def build_event(raw: Mapping[str, Any]) -> Event:  # сырые данные → карточка
    for name in REQUIRED_FIELDS:  # проверяем каждую обязательную графу
        if name not in raw:  # если графы нет
            raise InvalidEventError(f"нет обязательного поля {name!r}")

    try:  # пробуем разобрать дату
        timestamp = datetime.fromisoformat(raw["timestamp"])  # текст → дата
    except (ValueError, TypeError) as exc:  # не получилось
        raise InvalidTimestampError(f"неверная метка времени {raw['timestamp']!r}") from exc
    if timestamp.tzinfo is None:  # у даты нет часового пояса
        timestamp = timestamp.replace(tzinfo=UTC)  # ставим UTC

    try:  # пробуем найти уровень в списке
        level = Level(raw["level"])  # "ERROR" → Level.ERROR
    except ValueError as exc:  # такого уровня нет
        raise InvalidEventError(f"неизвестный уровень {raw['level']!r}") from exc

    source = raw["source"]  # достаём источник
    if not isinstance(source, str) or not source.strip():  # не строка или пустая
        raise InvalidEventError("source должен быть непустой строкой")

    message = raw["message"]  # достаём текст
    if not isinstance(message, str):  # не строка
        raise InvalidEventError("message должен быть строкой")

    return Event(timestamp, level, source, message)  # всё хорошо: собираем карточкуCLI