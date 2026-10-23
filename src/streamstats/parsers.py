import csv  # чтение таблиц CSV
import json  # разбор JSON-текста
import logging  # журнал предупреждений
from collections.abc import Callable, Iterator  # только для подписей
from dataclasses import dataclass  # «анкета» для счётчика
from pathlib import Path  # тип «путь», для подписи

from .errors import InvalidEventError, UnsupportedFormatError  # наши ошибки
from .models import (  # обязательные графы, карточка, «охранник»
    REQUIRED_FIELDS,
    Event,
    build_event,
)

logger = logging.getLogger(__name__)  # журнал для этого файла


@dataclass  # «анкета»
class ParseStats:  # счётчик пропущенных строк
    skipped: int = 0  # сколько пропущено, в начале 0


def _handle_bad_line(path, line_no, exc, skip_invalid, stats):  # что делать с плохой строкой
    message = f"{path}, строка {line_no}: {exc}"  # сообщение: файл, номер строки, причина
    if not skip_invalid:  # если режим пропуска выключен
        raise type(exc)(message) from exc  # останавливаем всё, бросая ошибку того же вида
    logger.warning("Пропущена строка. %s", message)  # иначе пишем WARNING в журнал
    if stats is not None:  # если счётчик передан
        stats.skipped += 1  # +1 пропущенная строка


def _event_from_json_line(line):  # одна JSONL-строка → карточка
    try:  # пробуем разобрать JSON
        raw = json.loads(line)  # текст → словарь
    except json.JSONDecodeError as exc:  # текст сломан
        raise InvalidEventError(f"некорректный JSON: {exc.msg}") from exc  # наша ошибка
    if not isinstance(raw, dict):  # валидный JSON, но не словарь
        raise InvalidEventError("строка должна быть JSON-объектом")
    return build_event(raw)  # отдаём


def _event_from_csv_row(row):  # одна строка CSV → карточка
    if None in row:  # значений больше, чем столбцов
        raise InvalidEventError("в строке больше столбцов, чем в заголовке")
    if None in row.values():  # значений меньше, чем столбцов
        raise InvalidEventError("в строке меньше столбцов, чем в заголовке")
    return build_event(row)  # отдаём «охраннику»


def parse_jsonl(
    path: str | Path,  # путь к файлу
    *,  # всё ниже передаётся только по имени
    skip_invalid: bool = False,  # пропускать ли плохие строки
    stats: ParseStats | None = None,  # счётчик пропущенных (необязателен)
) -> Iterator[Event]:  # отдаёт карточки по одной
    with open(path, encoding="utf-8") as file:  # открываем файл (русские буквы читаются)
        for line_no, line in enumerate(file, start=1):  # идём по строкам, номера с 1
            if not line.strip():  # пустая строка
                continue
            try:  # пробуем сделать карточку
                event = _event_from_json_line(line)
            except InvalidEventError as exc:  # не вышло (включая плохую метку)
                _handle_bad_line(path, line_no, exc, skip_invalid, stats)  # остановка или пропуск
                continue
            yield event  # отдаём карточку и ждём следующий запрос


def parse_csv(
    path: str | Path,
    *,
    skip_invalid: bool = False,
    stats: ParseStats | None = None,
) -> Iterator[Event]:
    with open(path, encoding="utf-8-sig", newline="") as file:  # utf-8-sig убирает метку Excel; newline="" для csv
        reader = csv.DictReader(file)  # читатель: первая строка = заголовок, дальше словари
        if reader.fieldnames is None:  # файл пустой, заголовка нет
            return  # ничего не отдаём
        missing = [name for name in REQUIRED_FIELDS if name not in reader.fieldnames]  # каких столбцов нет
        if missing:  # если чего-то не хватает
            raise InvalidEventError(
                f"{path}, строка 1: в заголовке нет столбцов {missing}"
            )  # ошибка всего файла
        for row in reader:  # по строкам данных
            try:
                event = _event_from_csv_row(row)  # пробуем сделать карточку
            except InvalidEventError as exc:
                _handle_bad_line(path, reader.line_num, exc, skip_invalid, stats)  # line_num: номер строки
                continue
            yield event


ParserFunc = Callable[..., Iterator[Event]]  # короткое имя для подписи «функция-парсер»

PARSERS: dict[str, ParserFunc] = {  # «диспетчер»: слово → нужный парсер
    "csv": parse_csv,
    "jsonl": parse_jsonl,
}


def parse_file(
    path: str | Path,
    fmt: str,  # название формата: "csv" или "jsonl"
    *,
    skip_invalid: bool = False,
    stats: ParseStats | None = None,
) -> Iterator[Event]:
    if fmt not in PARSERS:  # формата нет в словаре
        raise UnsupportedFormatError(f"неподдерживаемый формат {fmt!r}")  # наша ошибка
    return PARSERS[fmt](path, skip_invalid=skip_invalid, stats=stats)  # запускаем нужный парсер